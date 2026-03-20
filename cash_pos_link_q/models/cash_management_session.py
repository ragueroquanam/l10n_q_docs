from odoo import models


class CashManagementSessionInherit(models.Model):
    _inherit = 'cash.management.session'

    def action_view_incoming_payments(self):
        res = super().action_view_incoming_payments()
        terminal = self.config_id.pos_payment_terminal_id.id
        if 'context' in res:
            res['context'].update({'default_pos_payment_terminal_id': terminal})
        else:
            res['context'] = {'default_pos_payment_terminal_id': terminal}
        return res

    def action_view_outgoing_payments(self):
        res = super().action_view_outgoing_payments()
        terminal = self.config_id.pos_payment_terminal_id.id
        if 'context' in res:
            res['context'].update({'default_pos_payment_terminal_id': terminal})
        else:
            res['context'] = {'default_pos_payment_terminal_id': terminal}
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def action_register_payment(self):
        res = super().action_register_payment()
        default_pos_payment_terminal_id = self.env.context.get('default_pos_payment_terminal_id', False)
        if not default_pos_payment_terminal_id:
            return res
        if 'context' in res:
            res['context'].update({'default_pos_payment_terminal_id': default_pos_payment_terminal_id})
        else:
            res['context'] = {'default_pos_payment_terminal_id': default_pos_payment_terminal_id}
        return res
