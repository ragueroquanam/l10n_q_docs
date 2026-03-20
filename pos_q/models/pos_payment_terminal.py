# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosPaymentTerminal(models.Model):
    _name = 'pos.payment.terminal'
    _description = 'Terminal de Pago POS'
    _order = 'pos_id'

    pos_id = fields.Char(string="Número de terminal asignado al POS", size=10, required=True)
    branch = fields.Char(string="Identificador de la sucursal", size=100, required=True)
    client_app_id = fields.Char(string="Identificador de la caja", size=100, required=True)
    active = fields.Boolean(string="Activo", default=True)
    provider_id = fields.Many2one(
        comodel_name='pos.payment.provider',
        string='Proveedor de Pago',
        required=True,
        ondelete='restrict'
    )

    @api.depends('provider_id', 'pos_id')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.provider_id.name} {record.pos_id}" if record.provider_id else record.pos_id
