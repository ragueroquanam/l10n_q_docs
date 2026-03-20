from odoo import models, fields


class CashManagementConfig(models.Model):
    _inherit = 'cash.management.config'

    pos_payment_terminal_id = fields.Many2one(
        comodel_name='pos.payment.terminal',
        string='Terminal de Pago POS',
        domain="[('provider_id.code', '=', 'poslink')]"
    )
