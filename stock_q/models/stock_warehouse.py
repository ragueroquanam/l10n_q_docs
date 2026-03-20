# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    responsible_ids = fields.Many2many('res.users', string='Responsables')

    def get_search_domain(self, domain):
        domain_responsibles = self.get_search_domain_responsible()
        if domain_responsibles and self._context.get('from_action_warehouse_form', False):
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
        return [('responsible_ids', 'in', [user.id])]

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not self.env.su:
            domain = self.get_search_domain(domain)
        return super(StockWarehouse, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                      orderby=orderby, lazy=lazy)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if not self.env.su:
            domain = self.get_search_domain(domain)
        return super(StockWarehouse, self)._search(domain, offset=offset, limit=limit, order=order)
