from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApprovalRoute(models.Model):
    _inherit = 'approval.route'

    is_default = fields.Boolean(string="Ruta por defecto")
    is_default_label = fields.Char(
        string="Es ruta crítica",
        compute='_compute_is_default_label',
        store=False,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    def _compute_is_default_label(self):
        for route in self:
            route.is_default_label = "Sí" if route.is_default else "No"

    @api.constrains('model_id', 'is_default', 'active')
    def _check_unique_default_route(self):
        for route in self:
            if (
                route.is_default
                and route.active
                and self.search_count([
                    ('id', '!=', route.id),
                    ('model_id', '=', route.model_id.id),
                    ('is_default', '=', True),
                    ('active', '=', True),
                    ('company_id', '=', route.company_id.id),
                ])
            ):
                raise ValidationError(
                    _("Ya existe una ruta activa por la misma Compañía marcada por defecto")
                )
