from odoo import models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        journal_currency = self.journal_id.currency_id or self.env.company.currency_id
        move_ids = self.line_ids.mapped('move_id')
        any_invoice_multicurrency = move_ids.filtered(lambda inv: inv.currency_id != journal_currency)
        if len(move_ids) > 1 and any_invoice_multicurrency:
            raise UserError(_("Para realizar estos pagos debe ir por el botón Pagar en múltiples formas"))
        return super().action_create_payments()
        

    def _get_custom_amount_payment_difference(self, amount_in_wizard_curreny=None):
        self.ensure_one()
        if not self.payment_date:
            return float(0)
        else:
            total_amount_values = self._get_total_amounts_to_pay(self.batches)
            if self.installments_mode in ('overdue', 'next', 'before_date'):
                _amount_for_difference = amount_in_wizard_curreny or total_amount_values['amount_for_difference']
                return _amount_for_difference - self.amount
            elif self.installments_mode == 'full':
                _full_amount_for_difference = amount_in_wizard_curreny or total_amount_values['full_amount_for_difference']
                return _full_amount_for_difference - self.amount
            else:
                _amount_for_difference = amount_in_wizard_curreny or total_amount_values['amount_for_difference']
                return _amount_for_difference - self.amount