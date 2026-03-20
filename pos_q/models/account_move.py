# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    pos_ticket = fields.Char(
        string="Ticket POS",
        compute="_compute_pos_fields",
        store=True
    )
    pos_batch_number = fields.Char(
        string="Lote POS",
        compute="_compute_pos_fields",
        store=True
    )
    pos_authorization_code = fields.Char(
        string="Autorización POS",
        compute="_compute_pos_fields",
        store=True
    )

    @api.depends('payment_id', 'payment_id.ticket', 'payment_id.batch_number', 'payment_id.authorization_code')
    def _compute_pos_fields(self):
        for line in self:
            payment = line.payment_id
            if payment:
                line.pos_ticket = payment.ticket or False
                line.pos_batch_number = payment.batch_number or False
                line.pos_authorization_code = payment.authorization_code or False
            else:
                line.pos_ticket = False
                line.pos_batch_number = False
                line.pos_authorization_code = False
