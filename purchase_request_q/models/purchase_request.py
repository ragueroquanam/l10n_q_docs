from odoo import fields, models, api


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_form_edition_disabled = fields.Boolean(
        "¿Está deshabilitado el formulario para edición?",
        compute="_compute_is_form_edition_disabled",
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Proveedor',
        domain=[('supplier_rank', '>', 0)],
        required=False,
    )

    @api.depends('state')
    def _compute_is_form_edition_disabled(self):
        is_request_user = self.env.user.has_group("purchase_request.group_purchase_request_user")
        is_request_manager = self.env.user.has_group("purchase_request.group_purchase_request_manager")
        is_user_restricted = is_request_user and not is_request_manager
        for record in self:
            record.is_form_edition_disabled = (is_user_restricted and record.state != "draft") or record.state == "done"
