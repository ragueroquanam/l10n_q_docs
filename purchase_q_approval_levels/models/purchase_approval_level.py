from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PurchaseApprovalLevel(models.Model):
    _name = 'purchase.approval.level'
    _description = 'Approval levels'

    name = fields.Char(string='Nivel', required=True)
    min_amount = fields.Float(string='Monto Mínimo', required=True)
    max_amount = fields.Float(string='Monto Máximo', required=True)
    user_groups = fields.Many2many('res.groups', string='Grupos de Usuarios',
                                   help='Grupos de usuarios autorizados para este nivel'
                                   )

    @api.constrains('min_amount', 'max_amount')
    def _check_amounts(self):
        for record in self:
            if record.min_amount and record.max_amount:
                if record.min_amount > record.max_amount:
                    raise ValidationError(_("El monto mínimo no puede ser mayor al monto máximo."))

    def get_next_approval_level(self, total_amount, last_approval_level):
        approval_level = self.search([
            ('min_amount', '<=', total_amount),
            ('max_amount', '>=', total_amount)
        ], limit=1)

        if last_approval_level:
            max_amount = last_approval_level.max_amount
        else:
            max_amount = float(-1)

        return self.search(
            [('min_amount', '>', max_amount), ('max_amount', '<=', approval_level.max_amount)],
            order="min_amount asc", limit=1
        )

    def get_approval_users_emails(self):
        if self.user_groups:
            return ','.join(self.user_groups.mapped('users.partner_id.email'))

    def get_last_approval_level(self):
        return self.sudo().search([], order="max_amount desc", limit=1)
