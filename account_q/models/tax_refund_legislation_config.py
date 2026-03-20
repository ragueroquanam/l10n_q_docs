# -*- coding: utf-8 -*-

from odoo import fields, models, api


class TaxRefundLegislationConfig(models.Model):
    _name = 'tax.refund.legislation.config'
    _description = 'Configuración para Devolución de Impuestos'

    description = fields.Char(string='Descripción')
    law_reference = fields.Char(string='Ley')
    max_amount = fields.Float(string='Monto Máximo')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    tax_ids = fields.Many2many(
        'account.tax',
        'tax_refund_legislation_tax_rel',
        'config_id',
        'tax_id',
        string='Impuestos'
    )
    document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        string='Documento que aplica',
        help="Tipo de documento fiscal al que aplica la devolución de impuestos."
    )

    @api.depends('description', 'law_reference')
    def _compute_display_name(self):
        for rec in self:
            parts = [
                rec.description or '',
                f"({rec.law_reference})" if rec.law_reference else ''
            ]
            rec.display_name = ' '.join(filter(None, parts))