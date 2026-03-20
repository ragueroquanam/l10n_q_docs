from odoo import models


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    def _compute_account_id(self):
        super()._compute_account_id()

        for move in self.mapped("move_id"):
            forced_account_id = move.forced_account_id.id
            if forced_account_id:
                for line in self.filtered(lambda line: line.display_type == 'payment_term'):
                    line.account_id = forced_account_id
