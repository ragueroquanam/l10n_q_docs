# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    transact_currency_code = fields.Char(string='Código de moneda', help='Código de asignación de moneda para el POS')

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Incluye transact_currency_code en los datos cargados para POS"""
        fields = super()._load_pos_data_fields(config_id)
        fields.append('transact_currency_code')
        return fields
