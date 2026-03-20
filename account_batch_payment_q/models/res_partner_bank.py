# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    account_type = fields.Selection(
        string='Tipo de cuenta',
        selection=[
            ('cc', 'Cuenta corriente'),
            ('ca', 'Caja de ahorro'),
            ('cr', 'Cuenta recaudadora'),
            ('cpf', 'Cuenta a Plazo fijo'),
        ],
    )
