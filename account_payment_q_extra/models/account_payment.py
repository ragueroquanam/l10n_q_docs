from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    additional_info = fields.Text(string="Datos adicionales")


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    additional_info = fields.Text(string="Datos adicionales")

    def _create_payments(self):
        payments = super()._create_payments()
        payments.write({
            'additional_info': self.additional_info,
        })
        return payments
