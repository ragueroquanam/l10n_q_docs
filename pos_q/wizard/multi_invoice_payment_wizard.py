# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MultiInvoicePaymentWizard(models.TransientModel):
    _inherit = 'multi.invoice.payment.wizard'

    pos_payment_terminal_id = fields.Many2one(comodel_name='pos.payment.terminal', string='Terminal de Pago POS')

class MultiInvoicePaymentLine(models.TransientModel):
    _inherit = 'multi.invoice.payment.line'

    # POS fields
    is_credit = fields.Boolean(string='Crédito', default=False)
    pos_payment_terminal_id = fields.Many2one(comodel_name='pos.payment.terminal', string='Terminal de Pago POS')
    installment_qty = fields.Integer(string='Cuotas', default=1)
    is_pos_method = fields.Boolean(string="Es POS", compute='_compute_is_pos_method', store=False)
    pos_invoice_number = fields.Char(string='Nro Factura', size=12)
    ticket = fields.Char(string='Ticket', size=10)
    batch_number = fields.Char(string='Lote', size=10)
    authorization_code = fields.Char(string='Autorización', size=50)
    is_pos_manual = fields.Boolean(string="POS Manual", compute='_compute_is_pos_method', store=False)

    @api.depends('payment_method_line_id.payment_method_id.code')
    def _compute_is_pos_method(self):
        for rec in self:
            rec.is_pos_method = rec.payment_method_line_id.payment_method_id.code in ['pos', 'pos_manual']
            rec.is_pos_manual = rec.payment_method_line_id.payment_method_id.code == 'pos_manual'

    def _prepare_payment_line_values(self, amount_to_register_line_currency):
        vals = super()._prepare_payment_line_values(amount_to_register_line_currency)
        if self.is_pos_method:
            vals.update({
                'is_pos_method': self.is_pos_method,
                'is_pos_manual': self.is_pos_manual,
                'pos_payment_terminal_id': self.pos_payment_terminal_id.id,
                'is_credit': self.is_credit,
                'installment_qty': self.installment_qty,
                'pos_invoice_number': self.pos_invoice_number,
                'ticket': self.ticket,
                'batch_number': self.batch_number,
                'authorization_code': self.authorization_code,
            })
        return vals

