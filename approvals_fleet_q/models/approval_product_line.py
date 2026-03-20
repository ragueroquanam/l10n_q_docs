from odoo import models, api, fields
from odoo.exceptions import ValidationError


class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    is_update_quantity_available = fields.Boolean(
        string='¿Está disponible la actualización de la cantidad?',
        compute='_compute_is_update_quantity_available',
        store=False
    )

    @api.constrains('approval_request_id')
    def _check_fuel_request_single_line(self):
        for line in self:
            request = line.approval_request_id
            if request.is_fuel_request and self.search_count([
                ('approval_request_id', '=', request.id),
                ('id', '!=', line.id)
            ]):
                raise ValidationError("Solo se permite una línea de Producto para una Solicitud de Combustible")

    @api.depends(
        'approval_request_id.request_status',
        'approval_request_id.is_fuel_request',
        'approval_request_id.is_service_generated',
        'approval_request_id.purchase_order_count'
    )
    def _compute_is_update_quantity_available(self):
        for line in self:
            is_approved = line.approval_request_id.request_status == 'approved'
            is_fuel_request = line.approval_request_id.is_fuel_request
            is_any_service_generated = line.approval_request_id.is_service_generated
            is_purchase_order_generated = line.approval_request_id.purchase_order_count > 0
            line.is_update_quantity_available = (
                is_approved and is_fuel_request
                and not is_any_service_generated
                and not is_purchase_order_generated
            )

    def button_update_quantity(self):
        action = self.env['base.wizard'].launch_wizard(
            env=self.env,
            model_name='approval.product.line',
            method_name='update_quantity',
            active_ids=self.ids,
            show_fields=['base_integer'],
            label_map={'base_integer': 'Cantidad'},
            default_fields={'base_integer': self.quantity},
            wizard_name='Actualizar cantidad',
        )
        return action

    def update_quantity(self, dict):
        new_quantity = dict.get('base_integer')
        self.write({'quantity': new_quantity})
