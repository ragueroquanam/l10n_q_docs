from odoo import fields, models, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    check_number = fields.Char(string="Nro. de Cheque")
    check_due_date = fields.Date(string="Fecha de vencimiento")
    payment_method_is_check = fields.Boolean(
        string="¿Es Cheque?",
        related="payment_method_line_id.is_check",
        store=True,
    )

    @api.onchange('payment_method_line_id', 'journal_id')
    def _onchange_journal_id(self):
        if not self.payment_method_line_id or not self.payment_method_line_id.is_check:
            self.check_number = False
            self.check_due_date = False

    def action_create_payments(self):
        self.ensure_one()
        if self.payment_method_is_check and self.check_number and self.check_due_date:
            self.write({
                'communication': (
                    f"{self.check_number}: "
                    f"{self.check_due_date.strftime('%d-%m-%Y')}: "
                    f"{self.communication or ''}"
                )
            })

        res = super().action_create_payments()

        if self.payment_method_is_check:
            move_ids = self.line_ids.mapped('move_id.id')

            self.env['account.payment'].search([
                ('invoice_ids', 'in', move_ids)
            ]).write({
                'check_number': self.check_number,
                'check_due_date': self.check_due_date,
            })

        return res
