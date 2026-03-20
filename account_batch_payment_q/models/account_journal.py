# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    file_config_id = fields.Many2one('account.bank.payment.file.config', string='Archivo de pagos')
    file_config_ids = fields.Many2many('account.bank.payment.file.config', string='Archivos de pagos')
