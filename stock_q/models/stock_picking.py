# -*- coding: utf-8 -*-

import json
from odoo import api, fields, models
from odoo.osv import expression
from ast import literal_eval


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    location_dest_id_domain = fields.Char(
        compute='_compute_location_dest_id_domain',
        store=False
    )
    location_id_domain = fields.Char(
        compute='_compute_location_id_domain',
        store=False
    )

    def get_locations_with_access(self):
        user = self.env.user

        accessible_location_ids = set()
        all_warehouses = self.env['stock.warehouse'].sudo().search([])
        warehouses_user_responsible = all_warehouses.filtered(lambda x: user in x.responsible_ids)

        for wh in all_warehouses:
            all_locations = self.env['stock.location'].sudo().search(
                [('warehouse_id', '=', wh.id)])  # ('usage', 'in', ['internal', 'transit']),

            if not all_locations:
                continue

            locations_user_responsible = all_locations.filtered(lambda x: user in x.responsible_ids)
            if not locations_user_responsible and (
                    not warehouses_user_responsible or wh in warehouses_user_responsible):
                accessible_location_ids.update(all_locations.ids)

        return list(accessible_location_ids)

    @api.depends_context('loc_dest_id_responsible_domain', 'user_id')
    @api.depends('company_id')
    def _compute_location_dest_id_domain(self):
        for rec in self:
            company_id = rec.company_id
            if company_id:
                domain = [('company_id', 'in', [rec.company_id.id, False])]
            else:
                domain = [('company_id', '=', False)]
            if self.env.context.get('loc_dest_id_responsible_domain', False):
                user_ids = self.get_search_domain_user_ids()
                warehouses_ids = self.get_search_domain_warehouses_ids()
                if user_ids:
                    if warehouses_ids:
                        domain += [('responsible_ids', 'in', user_ids)]
                    else:
                        locations_ids = self.get_locations_with_access()
                        if locations_ids:
                            domain += ['|', ('responsible_ids', 'in', user_ids), ('id', 'in', locations_ids)]
                        else:
                            domain += [('responsible_ids', 'in', user_ids)]

                if warehouses_ids:
                    domain += [('warehouse_id', 'in', warehouses_ids)]
            rec.location_dest_id_domain = json.dumps(domain)

    @api.depends_context('ori_loc_id_responsible_domain', 'user_id')
    @api.depends('company_id')
    def _compute_location_id_domain(self):
        for rec in self:
            company_id = rec.company_id
            if company_id:
                domain = [('company_id', 'in', [rec.company_id.id, False])]
            else:
                domain = [('company_id', '=', False)]
            if self.env.context.get('ori_loc_id_responsible_domain', False):
                user_ids = self.get_search_domain_user_ids()
                warehouses_ids = self.get_search_domain_warehouses_ids()
                if user_ids:
                    if warehouses_ids:
                        domain += [('responsible_ids', 'in', user_ids)]
                    else:
                        locations_ids = self.get_locations_with_access()
                        if locations_ids:
                            domain += ['|', ('responsible_ids', 'in', user_ids), ('id', 'in', locations_ids)]
                        else:
                            domain += [('responsible_ids', 'in', user_ids)]

                if warehouses_ids:
                    domain += [('warehouse_id', 'in', warehouses_ids)]
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

    def get_search_domain(self, domain):
        user_ids = self.get_search_domain_user_ids()
        warehouses_ids = self.get_search_domain_warehouses_ids()
        if self._context.get('loc_dest_id_responsible_domain', False):
            domain_responsibles = []
            if user_ids:
                if warehouses_ids:
                    domain_responsibles += [('location_dest_id.responsible_ids', 'in', user_ids)]
                else:
                    locations_ids = self.get_locations_with_access()
                    if locations_ids:
                        domain_responsibles += ['|', ('location_dest_id.responsible_ids', 'in', user_ids),
                                                ('location_dest_id.id', 'in', locations_ids)]
                    else:
                        domain_responsibles += [('location_dest_id.responsible_ids', 'in', user_ids)]

            if warehouses_ids:
                domain_responsibles += [('location_dest_id.warehouse_id', 'in', warehouses_ids)]
            domain = expression.AND([expression.normalize_domain(domain), domain_responsibles])
        if self._context.get('ori_loc_id_responsible_domain', False):
            domain_responsibles = []
            if user_ids:
                if warehouses_ids:
                    domain_responsibles += [('location_id.responsible_ids', 'in', user_ids)]
                else:
                    locations_ids = self.get_locations_with_access()
                    if locations_ids:
                        domain_responsibles += ['|', ('location_id.responsible_ids', 'in', user_ids),
                                                ('location_id.id', 'in', locations_ids)]
                    else:
                        domain_responsibles += [('location_id.responsible_ids', 'in', user_ids)]

            domain = expression.AND([expression.normalize_domain(domain), domain_responsibles])
        return domain

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # Verificar si en args hay una condición sobre 'id'
        id_filter_present = any(
            condition[0] == 'id' and condition[1] in ('=', 'in') for condition in domain if
            isinstance(condition, (list, tuple))
        )
        if not self.env.su and not id_filter_present:
            domain = self.get_search_domain(domain)
        return super(StockPicking, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                    orderby=orderby, lazy=lazy)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        # Verificar si en args hay una condición sobre 'id'
        id_filter_present = any(
            condition[0] == 'id' and condition[1] in ('=', 'in') for condition in domain if
            isinstance(condition, (list, tuple))
        )
        if not self.env.su and not id_filter_present:
            domain = self.get_search_domain(domain)
        return super(StockPicking, self)._search(domain, offset=offset, limit=limit, order=order)

    @api.depends('picking_type_id', 'partner_id')
    def _compute_location_id(self):
        def _get_responsible_location(location, picking, context_key):
            user_id = self.env.user.id
            accessible_locations = self.env['stock.picking'].get_locations_with_access()

            if not self.env.context.get(context_key, False) or \
               user_id in location.responsible_ids.ids or \
               location.id in accessible_locations:
                return location

            warehouse = picking.picking_type_id.warehouse_id
            if warehouse:
                return self.env['stock.location'].sudo().search([
                    ('warehouse_id', '=', warehouse.id),
                    ('responsible_ids', 'in', user_id)
                ], limit=1)
            return self.env['stock.location']

        for picking in self:
            if picking.state in ('cancel', 'done') or picking.return_id:
                continue
            picking = picking.with_company(picking.company_id)
            if picking.picking_type_id:
                location_src = picking.picking_type_id.default_location_src_id
                if location_src.usage == 'supplier' and picking.partner_id:
                    location_src = picking.partner_id.property_stock_supplier
                location_dest = picking.picking_type_id.default_location_dest_id
                if location_dest.usage == 'customer' and picking.partner_id:
                    location_dest = picking.partner_id.property_stock_customer

                # Se adiciona la validacion de responsables
                cpy_location_src = _get_responsible_location(location_src, picking, 'ori_loc_id_responsible_domain')
                cpy_location_dest = _get_responsible_location(location_dest, picking, 'loc_dest_id_responsible_domain')

                picking.location_id = cpy_location_src.id if cpy_location_src else False
                picking.location_dest_id = cpy_location_dest.id if cpy_location_dest else False


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def _get_action(self, action_xmlid):
        action = super()._get_action(action_xmlid)

        if 'context' in action:
            context = action['context']
            if isinstance(context, str):
                context = literal_eval(context)
            code = context.get('restricted_picking_type_code') or self.code
            if code == 'incoming':
                context.update({
                    'loc_dest_id_responsible_domain': True,
                })
            elif code in ('outgoing', 'internal'):
                context.update({
                    'ori_loc_id_responsible_domain': True,
                    'loc_dest_id_responsible_domain': False,
                })
            action['context'] = context
        return action

    def get_search_domain(self, domain):
        domain_responsibles = self.get_search_domain_responsible()
        if domain_responsibles and self._context.get('from_main_inventory_view', False):
            domain = expression.AND([expression.normalize_domain(domain), domain_responsibles])
        return domain

    def get_search_domain_responsible(self):
        user = self.env.user
        if user.has_group('stock.group_stock_manager'):
            return []

        # Buscar si el usuario es responsable de algun almacen
        responsable_locations = self.env['stock.warehouse'].sudo().search_count([
            ('responsible_ids', 'in', [user.id])
        ])

        if responsable_locations == 0:
            return []

        # Caso normal: tiene almacenes asignados
        return [('warehouse_id.responsible_ids', 'in', [user.id])]

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # Verificar si en args hay una condición sobre 'id'
        id_filter_present = any(
            condition[0] == 'id' and condition[1] in ('=', 'in') for condition in domain if
            isinstance(condition, (list, tuple))
        )
        if not self.env.su and not id_filter_present:
            domain = self.get_search_domain(domain)
        return super(StockPickingType, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                        orderby=orderby, lazy=lazy)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        # Verificar si en args hay una condición sobre 'id'
        id_filter_present = any(
            condition[0] == 'id' and condition[1] in ('=', 'in') for condition in domain if
            isinstance(condition, (list, tuple))
        )
        if not self.env.su and not id_filter_present:
            domain = self.get_search_domain(domain)
        return super(StockPickingType, self)._search(domain, offset=offset, limit=limit, order=order)
