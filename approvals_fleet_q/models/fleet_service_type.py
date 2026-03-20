from odoo import models, fields


class FleetServiceType(models.Model):
    _inherit = 'fleet.service.type'

    is_fuel_service = fields.Boolean(string='Es servicio de combustible')
