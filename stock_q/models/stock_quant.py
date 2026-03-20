# -*- coding: utf-8 -*-

import json

from odoo import api, fields, models
from odoo.osv import expression


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    location_id_domain = fields.Char(
        compute='_compute_domain_location_id',
        store=False
    )

    @api.depends_context('user_id')
    @api.depends('company_id')
    def _compute_domain_location_id(self):
        domain = []
        if self.env.user.has_group('stock.group_stock_user'):
            domain = [('usage', 'in', ('internal', 'transit'))]
            user_ids = self.get_search_domain_user_ids()
            warehouses_ids = self.get_search_domain_warehouses_ids()
            if user_ids:
                if warehouses_ids:
                    domain += [('responsible_ids', 'in', user_ids)]
                else:
                    locations_ids = self.env['stock.picking'].get_locations_with_access()
                    if locations_ids:
                        domain += ['|', ('responsible_ids', 'in', user_ids), ('id', 'in', locations_ids)]
                    else:
                        domain += [('responsible_ids', 'in', user_ids)]

            if warehouses_ids:
                domain += [('warehouse_id', 'in', warehouses_ids)]
        for rec in self:
            rec.location_id_domain = json.dumps(domain)

    def get_search_domain_warehouses_ids(self):
        user = self.env.user
        if user.has_group('stock.group_stock_manager'):
            return []

        # Buscar si el usuario es responsable de algun almacen
        responsable_warehouses = self.env['stock.warehouse'].sudo().search([
            ('responsible_ids', 'in', [user.id])
        ])

        if not responsable_warehouses:
            return []

        # Caso normal: tiene almacenes asignados
        return responsable_warehouses.ids

    def get_search_domain_user_ids(self):
        user = self.env.user
        if user.has_group('stock.group_stock_manager'):
            return []

        # Buscar si el usuario es responsable de alguna ubicación
        responsable_locations = self.env['stock.location'].sudo().search_count([
            ('responsible_ids', 'in', [user.id])
        ])

        if responsable_locations == 0:
            return []

        # Caso normal: tiene ubicaciones asignadas
        return [user.id]

    @api.model
    def action_view_inventory(self):
        action = super(StockQuant, self).action_view_inventory()
        domain = []
        user_ids = self.get_search_domain_user_ids()
        warehouses_ids = self.get_search_domain_warehouses_ids()
        if user_ids:
            if warehouses_ids:
                domain += [('location_id.responsible_ids', 'in', user_ids)]
            else:
                locations_ids = self.env['stock.picking'].get_locations_with_access()
                if locations_ids:
                    domain += ['|', ('location_id.responsible_ids', 'in', user_ids), ('location_id.id', 'in', locations_ids)]
                else:
                    domain += [('location_id.responsible_ids', 'in', user_ids)]

        if warehouses_ids:
            domain += [('location_id.warehouse_id', 'in', warehouses_ids)]
        if domain:
            action['domain'] = expression.AND([action['domain'], domain])

        return action

    @api.onchange('product_id', 'company_id')
    def _onchange_product_id(self):
        if self.location_id:
            return
        location_id = None
        if self.product_id.tracking in ['lot', 'serial']:
            previous_quants = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('location_id.usage', 'in', ['internal', 'transit'])], limit=1, order='create_date desc')
            if previous_quants:
                location_id = previous_quants.location_id
        if not self.location_id:
            company_id = self.company_id and self.company_id.id or self.env.company.id
            location_id = self.env['stock.warehouse'].search(
                [('company_id', '=', company_id)], limit=1
            ).lot_stock_id
        if location_id:
            user_id = self.env.user.id
            locations_ids = self.env['stock.picking'].get_locations_with_access()
            if (any(u.id == user_id for u in location_id.responsible_ids)) or (locations_ids and location_id.id in locations_ids):
                self.location_id = location_id
