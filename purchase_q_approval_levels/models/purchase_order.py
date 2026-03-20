from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    last_approval_level = fields.Many2one('purchase.approval.level', string='Último Nivel de Aprobación', copy=False)
    next_approval_level = fields.Many2one('purchase.approval.level', string='Próximo Nivel de Aprobación',
                                          compute='_compute_next_approval_level', store=True, copy=False)
    allow_approval_level = fields.Boolean('Habilitado para nivel de aprobacion',
                                          compute='_compute_allow_approval_level', copy=False)

    @api.depends('amount_total', 'last_approval_level', 'state')
    def _compute_next_approval_level(self):
        for order in self:
            if order.state != 'to approve':
                order.next_approval_level = self.env['purchase.approval.level']
            else:
                purchase_approval_level = self.env['purchase.approval.level']
                order.next_approval_level = purchase_approval_level.get_next_approval_level(order.amount_total_cc,
                                                                                            order.last_approval_level)

    @api.onchange('state')
    def _onchange_reset_level(self):
        if self.state != 'to approve':
            self.last_approval_level = self.env['purchase.approval.level']

    def _compute_allow_approval_level(self):
        for order in self:
            if order.state == 'to approve':
                approval_level = order.next_approval_level

                if approval_level and approval_level.user_groups:
                    user_groups_xml_ids = approval_level.user_groups.get_external_id().values()
                    order.allow_approval_level = any(self.env.user.has_group(group) for group in user_groups_xml_ids)
                else:
                    order.allow_approval_level = False
            else:
                order.allow_approval_level = False

    def button_approve(self, force=False):
        for order in self:
            order.write({'last_approval_level': order.next_approval_level})
            if order.next_approval_level:
                order.send_to_approve_notification_email()
        self_new = self.filtered(lambda order: not order.next_approval_level)
        super(PurchaseOrder, self_new).button_approve(force=force)
        for order in self_new:
            if order.state == 'purchase':
                order.last_approval_level = self.env['purchase.approval.level']
                order.send_approve_notification_email()

    def button_cancel(self):
        super(PurchaseOrder, self).button_cancel()
        for order in self:
            if order.state == 'cancel':
                order.last_approval_level = self.env['purchase.approval.level']
                order.send_cancel_notification_email()

    def button_confirm(self):
        super(PurchaseOrder, self).button_confirm()
        self.filtered(lambda order: order.state == 'to approve')._is_valid_amount()
        for order in self:
            if order.state == 'to approve' and order.next_approval_level:
                order.send_to_approve_notification_email()

    def _approval_allowed(self):
        self.ensure_one()
        if self.state == 'to approve' and not self.next_approval_level:
            return True
        else:
            return super()._approval_allowed()

    def _is_valid_amount(self):
        last_approval_level = self.env['purchase.approval.level'].get_last_approval_level()
        max_amount_configured = last_approval_level.max_amount
        for record in self:
            if last_approval_level and record.amount_total > max_amount_configured:
                raise ValidationError(
                    _("El monto total es mayor al monto máximo configurado para los niveles de aprobación.")
                )

    def send_to_approve_notification_email(self):
        template = self.env.ref('purchase_q_approval_levels.mail_template_purchase_order_to_approve_notification')
        template.send_mail(self.id)

    def send_approve_notification_email(self):
        template = self.env.ref('purchase_q_approval_levels.mail_template_purchase_order_approval_notification')
        template.send_mail(self.id)

    def send_cancel_notification_email(self):
        template = self.env.ref('purchase_q_approval_levels.mail_template_purchase_order_cancel_notification')
        template.send_mail(self.id)
