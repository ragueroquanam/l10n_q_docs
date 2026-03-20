import base64
import io
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountQPaymentFromFile(models.Model):
    _name = "account.q.payment.from.file"
    _description = "Pago desde Archivo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Referencia",
        required=True,
        default="/",
        # readonly=True,
        # states={"draft": [("readonly", False)]},
        copy=False,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("file_processed", "Archivo Procesado"),
            ("processed", "Procesado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        # readonly=True,
        # states={"draft": [("readonly", False)]},
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario de Pago",
        required=True,
        domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', company_id)]",
        # readonly=True,
        # states={"draft": [("readonly", False)]},
        tracking=True,
    )
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Método de Pago",
        required=True,
        domain="[('journal_id', '=', journal_id)]",
        # readonly=True,
        # states={"draft": [("readonly", False)]},
        tracking=True,
    )
    payment_date = fields.Date(
        string="Fecha",
        required=True,
        default=fields.Date.context_today,
        # readonly=True,
        # states={"draft": [("readonly", False)]},
        tracking=True,
    )
    file_name = fields.Char(string="Nombre del Archivo", readonly=True)
    file_data = fields.Binary(
        string="Archivo",
        required=True,
        # readonly=True,
        # states={"draft": [("readonly", False)]},
        attachment=True,
    )
    file_type = fields.Selection(
        [
            ("excel", "Excel (Red Pagos)"),
            ("txt", "TXT (Abitab)"),
        ],
        string="Tipo de Archivo",
        compute="_compute_file_type",
        store=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        "account.q.payment.from.file.line",
        "payment_file_id",
        string="Líneas",
        readonly=True,
    )
    line_count = fields.Integer(
        string="Total de Líneas",
        compute="_compute_line_stats",
        store=True,
    )
    line_processed_count = fields.Integer(
        string="Líneas Procesadas",
        compute="_compute_line_stats",
        store=True,
    )
    line_error_count = fields.Integer(
        string="Líneas con Error",
        compute="_compute_line_stats",
        store=True,
    )
    line_pending_count = fields.Integer(
        string="Líneas Pendientes",
        compute="_compute_line_stats",
        store=True,
    )
    total_amount = fields.Monetary(
        string="Monto Total",
        compute="_compute_total_amount",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="journal_id.currency_id",
        store=True,
        readonly=True,
    )

    def unlink(self):
        for record in self:
            if record.state == "processed":
                raise UserError(_("No se puede eliminar elementos procesados."))
        return super().unlink()

    @api.depends("file_name")
    def _compute_file_type(self):
        for record in self:
            if record.file_name:
                file_name_lower = record.file_name.lower()
                if file_name_lower.endswith((".xls", ".xlsx")):
                    record.file_type = "excel"
                elif file_name_lower.endswith(".txt"):
                    record.file_type = "txt"
                else:
                    record.file_type = False
            else:
                record.file_type = False

    @api.depends("line_ids.state", "line_ids.amount")
    def _compute_line_stats(self):
        for record in self:
            record.line_count = len(record.line_ids)
            record.line_processed_count = len(
                record.line_ids.filtered(lambda l: l.state == "processed")
            )
            record.line_error_count = len(
                record.line_ids.filtered(lambda l: l.state == "error")
            )
            record.line_pending_count = len(
                record.line_ids.filtered(lambda l: l.state == "pending")
            )

    @api.depends("line_ids.amount", "line_ids.state")
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(
                record.line_ids.filtered(lambda l: l.state != "error").mapped("amount")
            )

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        """Clear payment method when journal changes"""
        self.payment_method_line_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "account.q.payment.from.file"
                ) or "/"
        return super().create(vals_list)

    def action_process_file(self):
        """Process the uploaded file and create lines"""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Por favor cargue un archivo primero."))

        # Delete existing lines
        self.line_ids.unlink()

        # Process file based on type
        if self.file_type == "excel":
            self._process_excel_file()
        elif self.file_type == "txt":
            self._process_txt_file()
        else:
            raise UserError(_("Tipo de archivo inválido. Por favor cargue un archivo Excel o TXT."))

        self.state = "file_processed"
        self.message_post(
            body=_(
                "Archivo procesado exitosamente. %s líneas creadas." % len(self.line_ids)
            )
        )

    def _process_excel_file(self):
        """Process Excel file from Red Pagos"""
        try:
            import openpyxl
        except ImportError:
            raise UserError(
                _(
                    "La librería openpyxl no está instalada. "
                    "Por favor instálela con: pip install openpyxl"
                )
            )

        file_content = base64.b64decode(self.file_data)
        workbook = openpyxl.load_workbook(io.BytesIO(file_content))
        sheet = workbook.active

        # Expected columns: FECHA, TRACK, MONEDA, IMPORTE, MOVIMIENTO, SUB AGENCIA, CAJA
        line_vals_list = []
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(row):
                continue

            try:
                # Parse row data
                fecha = row[0] if len(row) > 0 else None
                track = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                currency_code = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                importe = float(row[3]) if len(row) > 3 and row[3] else 0.0
                movimiento = str(row[4]) if len(row) > 4 and row[4] else ""
                sub_agencia = str(row[5]) if len(row) > 5 and row[5] else ""
                caja = str(row[6]) if len(row) > 6 and row[6] else ""

                # Parse date
                if isinstance(fecha, datetime):
                    payment_date = fecha.date()
                elif isinstance(fecha, str):
                    try:
                        payment_date = datetime.strptime(fecha, "%d/%m/%Y").date()
                    except ValueError:
                        payment_date = self.payment_date
                else:
                    payment_date = self.payment_date

                # Currency mapping
                if currency_code == 'U$S':
                    currency = self.env.ref('base.USD')
                else:
                    currency = self.env.ref('base.UYU')

                line_vals_list.append(
                    {
                        "payment_file_id": self.id,
                        "sequence": row_idx,
                        "barcode": track,
                        "amount": importe,
                        "currency_code": currency_code,
                        "currency_id": currency.id,
                        "payment_date": payment_date,
                        "reference": movimiento,
                        "sub_agency": sub_agencia,
                        "cashier": caja,
                        "state": "pending",
                    }
                )
            except Exception as e:
                _logger.error("Error processing row %s: %s", row_idx, str(e))
                line_vals_list.append(
                    {
                        "payment_file_id": self.id,
                        "sequence": row_idx,
                        "barcode": "",
                        "amount": 0.0,
                        "state": "error",
                        "error_message": str(e),
                    }
                )

        if line_vals_list:
            self.env["account.q.payment.from.file.line"].create(line_vals_list)

    def _process_txt_file(self):
        """Process TXT file from Abitab"""
        file_content = base64.b64decode(self.file_data).decode("utf-8", errors="ignore")
        lines = file_content.strip().split("\n")

        line_vals_list = []
        for idx, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            try:
                # Parse fixed-width format
                # PMO1032805348290000000000000001280000000208100001488123006202300600205072023
                # PMO (3) + Account (7) + Receipt (5) + 00 (2) + Invoice (9) + 00 (2) +
                # Original Amount (5) + 00 (2) + Mora (9) + 00 (2) + Total (5) +
                # Decimals (2) + Currency (1) + Due Date (8) + Agency (3) + Sub Agency (3) + Payment Date (8)

                #PMO10142071030300 || 000000000 || 00 || 11178 || 81 || 00000 || 00 || 000011178|| 81 ||| 1 || 30092025 01202109092025
                #PMO10142071030300  barcode, buscar en el barcode en el barcode que contenga esta secuencia al principio

                #17:26 que no me interesan
                #26:28 no me interesa
                #28:33 no me interesa
                # la mora no me interesa


                line = line.replace(" ", "")
                line = line.replace("\r", "")
                line = line.replace("\n", "")
                if len(line) < 70:
                    raise ValueError("Line too short")

                barcode = line[0:17]  # PMO + Account + Receipt number (first 17 chars)
                payment_date_str = line[-8:]
                sub_agency = line[-11:-8]
                agency = line[-14:-11]
                date_due_str = line[-22:-14]
                currency_code = line[-23:-22]
                total_amount_str = line[-30:-23]

                # invoice_number = line[17:26].strip("0")  # Invoice (9 chars)
                # original_amount_str = line[28:33]  # Original amount (5 chars)
                # mora_str = line[35:44]  # Mora (9 chars)
                # decimals_mora_str = line[44:46]  # Decimals (2 chars)
                # total_amount_str = line[46:51]  # Total amount (5 chars)
                # decimals_str = line[51:53]  # Decimals (2 chars)
                # currency_code = line[53:54]  # Currency (1 char: 1=UYU, 2=USD)
                # due_date_str = line[54:62]  # Due date (8 chars: DDMMYYYY)
                # agency = line[62:65]  # Agency (3 chars)
                # sub_agency = line[65:68]  # Sub agency (3 chars)
                # payment_date_str = line[68:76]  # Payment date (8 chars: DDMMYYYY)

                # PMO1032805348290000000000000001280000000208100001488123006202300600205072023
                # Ejemplo: PMO10328053||4829||00000||000000128||000000020||810000148||81230062||02300600||20507202||3
                # Formato: PMO+Cuenta||Recibo||00||Factura||00||Monto Original||00||Mora||00||Total||Decimales||Moneda||Vto||Agencia||SubAgencia||F.Pago||
                
                # PMO1014207103030000000000000111788100000000000111788113009202501202109092025
                # Ejemplo: PMO10142071||03030||30000||000000000||011178810||000000000||01117881||13009202||50120210||9092025||
                # Formato: PMO+Cuenta||Recibo||00||Factura||00||Monto Original||00||Mora||00||Total||Decimales||Moneda||Vto||Agencia||SubAgencia||F.Pago||

                # Calculate amount
                if total_amount_str.isdigit():
                    amount = float(total_amount_str) / 100
                else:
                    amount = float(0)
                
                if date_due_str.isdigit():
                    date_due = datetime.strptime(date_due_str, "%d%m%Y").date()
                else:
                    date_due = self.payment_date
                
                payment_date_str = payment_date_str.replace("\r", "").replace("\n", "")
                if len(payment_date_str) > 8:
                    payment_date_str = payment_date_str[-8:]
                try:
                    payment_date = datetime.strptime(payment_date_str, "%d%m%Y").date()
                except ValueError:
                    payment_date = self.payment_date

                # Currency mapping
                currency_map = {"1": "UYU", "2": "USD"}
                currency = currency_map.get(currency_code, "UYU")
                if currency == "UYU":
                    currency = self.env.ref('base.UYU')
                else:
                    currency = self.env.ref('base.USD')

                line_vals_list.append(
                    {
                        "payment_file_id": self.id,
                        "sequence": idx,
                        "barcode": barcode,
                        "amount": amount,
                        # "mora": mora,
                        "currency_code": currency,
                        "currency_id": currency.id,
                        "payment_date": payment_date,
                        # "reference": invoice_number,
                        "sub_agency": sub_agency,
                        "agency": agency,
                        "state": "pending",
                    }
                )
            except Exception as e:
                _logger.error("Error processing line %s: %s", idx, str(e))
                line_vals_list.append(
                    {
                        "payment_file_id": self.id,
                        "sequence": idx,
                        "barcode": line[:17] if len(line) >= 17 else line,
                        "amount": 0.0,
                        "state": "error",
                        "error_message": str(e),
                    }
                )

        if line_vals_list:
            self.env["account.q.payment.from.file.line"].create(line_vals_list)

    def action_process_payments(self):
        """Process payments for all pending lines"""
        self.ensure_one()
        if self.state != "file_processed":
            raise UserError(_("Por favor procese el archivo primero."))

        pending_lines = self.line_ids.filtered(lambda l: l.state == "pending")
        if not pending_lines:
            raise UserError(_("No hay líneas pendientes para procesar."))

        for line in pending_lines:
            try:
                line._process_payment()
            except Exception as e:
                _logger.error("Error processing line %s: %s", line.id, str(e))
                line.write({"state": "error", "error_message": str(e)})

        # Check if all lines are processed
        if all(line.state in ["processed", "error"] for line in self.line_ids):
            self.state = "processed"
            self.message_post(
                body=_(
                    "Todos los pagos procesados. Exitosos: %s, Errores: %s"
                    % (self.line_processed_count, self.line_error_count)
                )
            )

    def action_reset_to_draft(self):
        """Reset to draft state"""
        self.ensure_one()
        self.line_ids.unlink()
        self.state = "draft"

    def action_view_payments(self):
        """View created payments"""
        self.ensure_one()
        payments = self.line_ids.mapped("payment_id")
        return {
            "name": _("Pagos"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "tree,form",
            "domain": [("id", "in", payments.ids)],
            "context": {"create": False},
        }

