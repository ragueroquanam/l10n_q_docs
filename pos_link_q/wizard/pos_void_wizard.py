# -*- coding: utf-8 -*-

from odoo import fields, models


class PosVoidWizard(models.TransientModel):
    _name = 'pos.void.wizard'
    _description = 'Void/Refund POS Payment Wizard'

    payment_id = fields.Many2one('account.payment', readonly=True)

    def action_confirm_manual(self):
        self.ensure_one()
        payment = self.payment_id
        payment.process_pos_void(manual=True)
        return {'type': 'ir.actions.act_window_close'}

    def action_confirm_pos(self):
        self.ensure_one()
        payment = self.payment_id
        response, trans_id, void_type = payment.process_pos_void(manual=False)
        return payment.handle_pos_void_response(response, trans_id, void_type)
