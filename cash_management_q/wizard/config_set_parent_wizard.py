# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class CashConfigSetParentWizard(models.TransientModel):
    _name = 'cash.config.set.parent.wizard'
    _description = 'Asignar Caja Padre'

    @api.model
    def default_get(self, fields_list):
        res = super(CashConfigSetParentWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        configs = self.env['cash.management.config'].browse(active_ids)

        if len(configs) < 2:
            raise UserError(_('Debe seleccionar al menos dos cajas para asignar una como padre.'))

        companies = set(configs.mapped('company_id.id'))
        company = configs[0].company_id
        company_currency = company.currency_id

        if len(companies) != 1:
            raise UserError(_('Todas las cajas deben pertenecer a la misma compañía.'))

        # Buscar la caja que tenga la moneda de la compañía o ninguna moneda
        parent_candidates = configs.filtered(
            lambda c: c.currency_id == company_currency or not c.currency_id
        )

        if len(parent_candidates) != 1:
            raise UserError(_(
                'Debe existir exactamente UNA caja que tenga la misma moneda que la compañía '
                'o no tenga moneda asignada, para poder definirla como padre.'
            ))

        parent_config = parent_candidates[0]
        res.update({
            'parent_id': parent_config.id,
            'config_ids': [(6, 0, configs.ids)],
        })
        return res

    parent_id = fields.Many2one('cash.management.config', string='Caja Padre', required=True)
    config_ids = fields.Many2many('cash.management.config', string='Cajas Hijas')

    def action_set_parent(self):
        self.ensure_one()
        child_configs = self.config_ids - self.parent_id
        if not child_configs:
            raise UserError(_('No hay cajas hijas a actualizar.'))

        child_configs.write({'parent_id': self.parent_id.id})
        return {'type': 'ir.actions.act_window_close'}
