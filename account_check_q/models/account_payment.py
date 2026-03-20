from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    check_number = fields.Char(string="Nro. de Cheque", copy=False)
    check_due_date = fields.Date(string="Fecha de vencimiento", copy=False)
    payment_method_is_check = fields.Boolean(
        string="¿Es Cheque?",
        related="payment_method_line_id.is_check",
        store=True,
    )

    @api.onchange('payment_method_line_id', 'journal_id')
    def _onchange_payment_method_line_id_journal_id(self):
        if not self.payment_method_line_id or not self.payment_method_line_id.is_check:
            self.check_number = False
            self.check_due_date = False

    def _get_aml_default_display_name_list(self):
        self.ensure_one()
        result = super()._get_aml_default_display_name_list()
        # if self.memo:  # lo dejo comemtando porque si el campo Memo esta vacio no me agrega lo de cheques - Daniela Q - PS07 14274

        existing_texts = [text for key, text in result if isinstance(text, str)]
        extra_info = []
        if self.check_number and all(self.check_number not in text for text in existing_texts):
            extra_info.append(self.check_number)
            if self.check_due_date:
                extra_info.append(self.check_due_date.strftime("%d-%m-%Y"))
        if extra_info:
            result.append(('sep', ": "))
            result.append(('extra_info', ": ".join(extra_info)))

        return result
