from odoo import models, fields, api, _
from odoo.addons.fleet.models.fleet_vehicle_model import FUEL_TYPES
from odoo.exceptions import ValidationError


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo')
    license_plate = fields.Char(string='Matrícula', related='vehicle_id.license_plate')
    driver_id = fields.Many2one('res.partner', string='Conductor')
    fuel_type = fields.Selection(FUEL_TYPES, 'Tipo de Combustible')
    odometer_value = fields.Float(string='Valor del Odómetro')
    is_fuel_request = fields.Boolean(
        related="category_id.is_fuel_request",
        string='Solicitud de Combustible',
        store=True
    )
    is_service_generated = fields.Boolean(string='Servicio Generado')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.license_plate = self.vehicle_id.license_plate
            self.driver_id = self.vehicle_id.driver_id.id
            self.fuel_type = self.vehicle_id.fuel_type
        else:
            self.license_plate = False
            self.driver_id = False
            self.fuel_type = False

    @api.constrains('vehicle_id')
    def _check_vehicle_required_if_fuel_request(self):
        for record in self:
            if record.is_fuel_request and not record.vehicle_id:
                raise ValidationError(_("Debe ingresar los datos del Vehiculo"))

    def action_generate_fleet_service(self):
        FleetService = self.env['fleet.vehicle.log.services']
        ServiceType = self.env['fleet.service.type']

        service_type = ServiceType.search([('is_fuel_service', '=', True)], limit=1)
        if not service_type:
            raise ValidationError(_("No se ha configurado un tipo de servicio de combustible en Flota."))

        for record in self:
            if not record.vehicle_id:
                raise ValidationError(_("Debe seleccionar un vehículo."))
            if not record.driver_id:
                raise ValidationError(_("Debe indicar un conductor."))

            product_line = record.product_line_ids[:1]
            if not product_line:
                raise ValidationError(_("No hay producto asociado para registrar la cantidad."))

            FleetService.create({
                'vehicle_id': record.vehicle_id.id,
                'purchaser_id': record.driver_id.id,
                'odometer': record.odometer_value,
                'vendor_id': record.partner_id.id,
                'date': fields.Date.today(),
                'service_type_id': service_type.id,
                'state': 'done',
                'description': f'Servicio generado desde la solicitud #{record.name}',
                'quantity': product_line.quantity,
            })

            record.is_service_generated = True
