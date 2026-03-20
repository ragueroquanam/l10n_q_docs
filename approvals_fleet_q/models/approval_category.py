from odoo import models, fields


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    is_fuel_request = fields.Boolean(string='Solicitud de Combustible')
