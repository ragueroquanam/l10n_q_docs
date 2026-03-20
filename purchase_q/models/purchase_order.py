from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_form_edition_disabled = fields.Boolean(
        '¿Está deshabilitado el formulario para edición?',
        compute='_compute_is_form_edition_disabled')

    @api.depends('state')
    def _compute_is_form_edition_disabled(self):
        for order in self:
            order.is_form_edition_disabled = order.state in ['to approve', 'purchase']
