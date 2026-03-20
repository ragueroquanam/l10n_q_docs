from odoo import models, fields


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    quantity = fields.Float('Cantidad', default=0.0)
