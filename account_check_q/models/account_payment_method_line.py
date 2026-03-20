from odoo import models, fields


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    is_check = fields.Boolean(string="¿Es Cheque?")
    journal_type = fields.Selection(
        related='journal_id.type',
        string="Journal Type",
        store=True
    )
