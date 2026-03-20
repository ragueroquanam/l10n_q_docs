"""Este módulo extiende account.payment para manejar rutas de aprobación."""
from odoo import models, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def default_get(self, fields_list):
        """Carga la ruta de aprobación por defecto si existe."""
        defaults = super().default_get(fields_list)
        if 'approval_route_id' in fields_list and not defaults.get('approval_route_id'):
            default_route = self.env['approval.route'].search([
                ('is_default', '=', True),
                ('active', '=', True),
                ('model', '=', self._name),
            ], limit=1)
            if default_route:
                defaults['approval_route_id'] = default_route.id
        return defaults

    def button_mass_approve(self):
        invalid_payments = self.filtered(lambda p: p.state != 'to approve')
        if invalid_payments:
            raise UserError(_("Only pending payments can be approved."))
        for payment in self:
            payment._action_approve()
            if payment._is_fully_approved():
                payment.action_post()


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)

        if 'approval_route_id' in fields and not defaults.get('approval_route_id'):
            default_route = self.env['approval.route'].search([
                ('model', '=', 'account.payment'),
                ('is_default', '=', True),
                ('active', '=', True),
            ], limit=1)
            if default_route:
                defaults['approval_route_id'] = default_route.id

        return defaults

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Actualiza la ruta de aprobación por defecto si la compañía cambia."""
        if self.company_id:
            self.approval_route_id = self.env['approval.route'].search([
                ('model', '=', 'account.payment'),
                ('is_default', '=', True),
                ('active', '=', True),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
        else:
            self.approval_route_id = False
