from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    forced_account_id = fields.Many2one('account.account',
                                        string="Cuenta forzada para cliente",
                                        check_company=True,
                                        domain="[('account_type', 'in', ('asset_receivable', 'liability_credit_card')), ('deprecated', '=', False)]",
                                        required=False)
