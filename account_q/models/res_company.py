# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_q_taxable_tax_ids = fields.Many2many(
        'account.tax',
        string='Impuestos Gravables',
        help="Impuestos que deben considerarse al calcular el Monto gravable en facturas."
    )