# -*- coding: utf-8 -*-

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_q_taxable_tax_ids = fields.Many2many(
        'account.tax',
        string='Impuestos Gravables',
        related='company_id.account_q_taxable_tax_ids',
        readonly=False
    )
