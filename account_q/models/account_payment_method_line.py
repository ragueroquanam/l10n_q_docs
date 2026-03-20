from odoo import models, fields


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    apply_vat_refund = fields.Boolean(
        string="Devolución de IVA",
        help="Marcar si este método de pago aplica devolución de IVA."
    )
    type = fields.Selection(
        selection=[
            ("common", "Cheque Común"),
            ("postdated", "Cheque Diferido"),
        ],
        string="Tipo",
    )
