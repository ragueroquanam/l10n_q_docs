import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountQPaymentFromFileLine(models.Model):
    _name = "account.q.payment.from.file.line"
    _description = "Línea de Pago desde Archivo"
    _order = "payment_file_id, sequence"

    payment_file_id = fields.Many2one(
        "account.q.payment.from.file",
        string="Archivo de Pago",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Secuencia", default=10)
    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("processed", "Procesado"),
            ("error", "Error"),
        ],
        string="Estado",
        default="pending",
        required=True,
    )
    barcode = fields.Char(
        string="Código de Barras",
        help="Código de barras del archivo usado para encontrar la factura",
        index=True,
    )
    amount = fields.Monetary(
        string="Monto",
        currency_field="currency_id",
    )
    mora = fields.Monetary(
        string="Mora",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        store=True,
    )
    currency_code = fields.Char(string="Código de Moneda", help="Código de moneda del archivo (UYU, USD, etc)")
    payment_date = fields.Date(string="Fecha de Pago")
    reference = fields.Char(string="Referencia", help="Referencia de pago del archivo")
    sub_agency = fields.Char(string="Sub Agencia")
    agency = fields.Char(string="Agencia")
    cashier = fields.Char(string="Caja")
    invoice_id = fields.Many2one(
        "account.move",
        string="Factura",
        help="Factura encontrada por código de barras",
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago",
        help="Pago creado desde esta línea",
    )
    error_message = fields.Text(string="Mensaje de Error")
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="payment_file_id.company_id",
        store=True,
        readonly=True,
    )

    def _process_payment(self):
        """Process payment for this line"""
        self.ensure_one()

        if self.state != "pending":
            raise UserError(_("La línea no está en estado pendiente."))

        # Find invoice by barcode
        invoice = self._find_invoice_by_barcode()
        if not invoice:
            self.write(
                {
                    "state": "error",
                    "error_message": _("Factura no encontrada para el código de barras: %s") % self.barcode,
                }
            )
            return

        self.invoice_id = invoice.id

        # Validate invoice state
        if invoice.payment_state in ["paid", "in_payment"]:
            self.write(
                {
                    "state": "error",
                    "error_message": _("La factura %s ya está pagada o en proceso de pago") % invoice.name,
                }
            )
            return

        # Validate amount
        # if not self._validate_amount_with_barcode(invoice):
        #     return

        # Create payment
        try:
            payment = self._create_payment(invoice)
            if payment:
                payment.action_post()

                self.write(
                    {
                        "state": "processed",
                        "payment_id": payment.id,
                        "error_message": False,
                    }
                )
        except Exception as e:
            _logger.error("Error creating payment: %s", str(e))
            self.write(
                {
                    "state": "error",
                    "error_message": _("Error creando el pago: %s") % str(e),
                }
            )

    def _find_invoice_by_barcode(self):
        """Find invoice by barcode"""
        if not self.barcode:
            return False

        # Try to find by file_barcode (short version for Abitab)
        invoice = self.env["account.move"].search(
            [
                ("move_type", "in", ["out_invoice", "out_receipt"]),
                ("state", "=", "posted"),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ("file_barcode", "ilike", f"{self.barcode}%"),
            ],
            limit=1,
        )

        return invoice

    def get_amount_from_invoice_barcode(self):
        """
        Obtiene el importe desde el código de barras de la factura asociada.
        
        Returns:
            float: Importe extraído del código de barras o 0.0 si no se puede extraer
        """
        if not self.invoice_id or not self.invoice_id.file_barcode:
            return 0.0
            
        return self._extract_amount_from_barcode(self.invoice_id.file_barcode)

    def _extract_amount_from_barcode(self, file_barcode):
        """
        Extrae el importe del código de barras en la posición específica.
        
        Formato esperado: PMO0422702453180031122024000000134002002100000008
        Posición del importe: 00000013400 (11 dígitos donde los 2 últimos son decimales)
        
        Args:
            file_barcode (str): Código de barras completo
            
        Returns:
            float: Importe extraído o 0.0 si no se puede extraer
        """
        if not file_barcode or len(file_barcode) < 36:
            return 0.0
            
        try:
            # La posición del importe está en los caracteres 24-34 (11 dígitos)
            # Considerando que el string empieza en posición 0
            amount_str = file_barcode[25:36]
            
            if not amount_str.isdigit():
                return 0.0
                
            # Los dos últimos dígitos son los decimales
            integer_part = amount_str[:-2]  # Primeros 9 dígitos
            decimal_part = amount_str[-2:]  # Últimos 2 dígitos
            
            # Convertir a float
            amount = float(f"{integer_part}.{decimal_part}")
            
            return amount
            
        except (ValueError, IndexError) as e:
            _logger.warning("Error extrayendo importe del código de barras %s: %s", file_barcode, str(e))
            return 0.0

    def _validate_amount_with_barcode(self, invoice, register_payment_wizard):
        """
        Valida el monto usando el importe extraído del código de barras de la factura.
        
        Args:
            invoice: Factura a validar
            
        Returns:
            bool: True si la validación es exitosa, False en caso contrario
        """
        if not invoice.file_barcode:
            return True  # Si no hay código de barras, no validamos
            
        # Extraer importe del código de barras
        barcode_amount = self._extract_amount_from_barcode(invoice.file_barcode)
        
        if barcode_amount == 0.0:
            self.write({
                "state": "error",
                "error_message": _(
                    "No se pudo extraer el importe del código de barras para la factura %s.",
                ) % (
                    invoice.name,
                ),
            })
            return False

        if self.payment_date > invoice.invoice_date_due:
            _is_invoice_amount = True
            _topay_amount = None #thereis normally behavior
        else:
            _is_invoice_amount = False
            _topay_amount = barcode_amount
        # Convertir _topay_amount a la moneda del wizard si es necesario
            if invoice.currency_id != register_payment_wizard.currency_id:
                _topay_amount = invoice.currency_id._convert(
                    _topay_amount,
                    register_payment_wizard.currency_id,
                    invoice.company_id,
                    self.payment_date or fields.Date.today(),
                    round=True
                )

        _difference = register_payment_wizard._get_custom_amount_payment_difference(_topay_amount)
        cond_to_fail_1 = _is_invoice_amount and _difference > float(0)
        cond_to_fail_2 = not _is_invoice_amount and _difference != float(0)
        if cond_to_fail_1 or cond_to_fail_2:
            self.write({
                "state": "error",
                "error_message": _(
                    "El monto no coincide con el monto a pagar para la factura %s.",
                ) % (
                    invoice.name,
                ),
            })
            return False
            
        return True

    def _create_payment(self, invoice):
        """Create payment for the invoice"""
        register_payment_wizard = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoice.ids
        ).create({
            'journal_id': self.payment_file_id.journal_id.id,
            'payment_date': self.payment_date or fields.Date.today(),
            'payment_method_line_id': self.payment_file_id.payment_method_line_id.id,
            'communication': self.reference or self.payment_file_id.name,
            "currency_id": self.currency_id.id,
            'amount': self.amount,
        })
        result = self._validate_amount_with_barcode(self.invoice_id, register_payment_wizard)
        if not result:
            return False

        wizard = register_payment_wizard.action_create_payments()
        payment_id = wizard.get('res_id')
        payment = self.env["account.payment"].browse(payment_id)
        return payment

    def action_reprocess(self):
        """Reprocess failed line"""
        self.ensure_one()
        if self.state != "error":
            raise UserError(_("Solo las líneas con error pueden ser reprocesadas."))

        self.write({"state": "pending", "error_message": False})
        self._process_payment()

    def action_view_invoice(self):
        """View related invoice"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No se encontró factura para esta línea."))

        return {
            "name": _("Factura"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "view_id": False,
        }

    def action_view_payment(self):
        """View related payment"""
        self.ensure_one()
        if not self.payment_id:
            raise UserError(_("No se creó pago para esta línea."))

        return {
            "name": _("Pago"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": self.payment_id.id,
            "view_mode": "form",
            "view_id": False,
        }

