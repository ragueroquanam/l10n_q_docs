# -*- coding: utf-8 -*-

from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['pos'] = {'mode': 'multi', 'type': ('bank', 'cash', 'credit')}
        res['pos_manual'] = {'mode': 'multi', 'type': ('bank', 'cash', 'credit')}
        return res
