# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    pos_discount_enabled = fields.Boolean(string='Aplica descuento por adquiriente', default=False)
    pos_validity_date = fields.Date(string='Periodo de vigencia')
