# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, UserError


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    is_checked = fields.Boolean(string="Comprobado")
    payment_count = fields.Integer(string="Cantidad de pagos", compute="_compute_payment_count", store=True)
    payment_total_amount_signed = fields.Monetary(
        string='Total por pagar',
        compute='_compute_payment_count',
        currency_field='currency_id',
        store=True,
    )

    def _get_methods_generating_files(self):
        payment_methods = super(
            AccountBatchPayment, self
        )._get_methods_generating_files()
        payment_methods.append(
            self.env.ref(
                "account_batch_payment.account_payment_method_batch_deposit"
            ).code
        )
        return payment_methods

    def validate_batch(self):
        """Verifies the content of a batch and proceeds to its sending if possible.
        If not, opens a wizard listing the errors and/or warnings encountered.
        """
        is_file_config_recheck = (
            self.journal_id.file_config_ids
            and any(file_config.is_recheck_file for file_config in self.journal_id.file_config_ids)
        )
        if self.payment_method_code == "batch_payment" and is_file_config_recheck:
            if not self.payment_ids:
                raise UserError(
                    _(
                        "No se puede validar un lote vacío. Primero agregue unos pagos."
                    )
                )

            if self.payment_ids.filtered(lambda p: p.state != "in_process"):
                raise ValidationError(
                    _("Se deben publicar todos los pagos para validar el lote.")
                )

            errors = []
            for file_config in self.journal_id.file_config_ids:
                errors.extend(file_config.with_context(batch_payment=self).check_payments_for_errors(self.payment_ids))
            
            if errors:
                return {
                    "type": "ir.actions.act_window",
                    "view_mode": "form",
                    "res_model": "account.batch.error.wizard",
                    "target": "new",
                    "res_id": self.env["account.batch.error.wizard"]
                    .create_from_errors_list(self, errors, [])
                    .id,
                }
            return super(AccountBatchPayment, self).validate_batch()
        else:
            return super(AccountBatchPayment, self).validate_batch()

    def _generate_export_file(self):
        self.ensure_one()
        if self.payment_method_code not in ["batch_payment"]:
            return super(AccountBatchPayment, self)._generate_export_file()

        Util = self.env['account.bank.payment.file.config'].with_context(batch_payment=self)
        payments = self.payment_ids.sorted(key=lambda r: r.date)
        if self.journal_id.file_config_ids:
            date_formatted = fields.Date.today().strftime("%d%m%y")
            for file_config in self.journal_id.file_config_ids:
                code = file_config.code
                if hasattr(Util, f"_generate_payment_file_{code}"):
                    payment_template = getattr(file_config.with_context(batch_payment=self), f"_generate_payment_file_{code}")(payments)
                    export_file_data = {
                        "file": base64.encodebytes(payment_template.encode()),
                        "filename": f"{file_config.name}_{date_formatted} S.txt",
                    }
                    self.export_file = export_file_data['file']
                    self.export_filename = export_file_data['filename']
                    self.export_file_create_date = fields.Date.today()
                    self.message_post(
                        attachments=[
                            (self.export_filename, base64.decodebytes(self.export_file)),
                        ]
                    )
        else:
            return super(AccountBatchPayment, self)._generate_export_file()
        
        return True

    def export_batch_payment(self):
        self.check_access('write')
        for record in self.sudo():
            record = record.with_company(record.journal_id.company_id)
            record._generate_export_file()

    def unlink(self):
        if self.filtered(lambda r: r.state != "draft"):
            raise UserError(
                _(
                    "No se puede eliminar un Pago por lotes en estado diferente a Borrador."
                )
            )
        return super(AccountBatchPayment, self).unlink()

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_total_amount_signed = sum(rec.payment_ids.mapped('amount_signed'))
            rec.payment_count = len(rec.payment_ids)
