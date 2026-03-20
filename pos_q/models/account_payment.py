# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_credit = fields.Boolean(string='Crédito', default=False)
    pos_payment_terminal_id = fields.Many2one(comodel_name='pos.payment.terminal', string='Terminal de Pago POS')
    taxable_amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False)
    invoice_amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False)
    installment_qty = fields.Integer(string='Cuotas', default=1)
    transaction_number = fields.Char(string='Nro. de Transacción', size=19)
    transaction_date_str = fields.Char(
        string='Fecha Transacción (DDMMAA)',
        size=6,
        help='Fecha de la transacción en formato DDMMAA, por ejemplo "020725"'
    )
    transaction_state = fields.Selection([
        ('not_start', 'No iniciado'),
        ('sent', 'Enviada'),
        ('approved', 'Aprobada'),
        ('error', 'Error')
    ], string='Estado de la Transacción')
    is_pos_method = fields.Boolean(string="Es POS", compute='_compute_is_pos_method', store=False)
    is_partial_payment = fields.Boolean(string='Pago parcial', default=False)
    partial_amount = fields.Monetary(string='Total a pagar', currency_field='currency_id')
    pos_invoice_number = fields.Char(string='Nro Factura', size=12)
    ticket = fields.Char(string='Ticket', size=10)
    batch_number = fields.Char(string='Lote', size=10)
    authorization_code = fields.Char(string='Autorización', size=50)
    card_number = fields.Char(string='Nro Tarjeta', size=50)
    is_pos_manual = fields.Boolean(string="POS Manual", compute='_compute_is_pos_method', store=False)
    acquirer = fields.Char(string='Adquiriente', size=100)
    tax_refund = fields.Char(string='Devolución de impuestos', size=10)
    pos_discount_enabled = fields.Boolean(string='Aplica descuento por adquiriente', default=False)
    payment_datetime = fields.Datetime(string='Fecha y hora del pago', help='Fecha y hora en que se realizó el pago')

    @api.depends('payment_method_line_id.payment_method_id.code')
    def _compute_is_pos_method(self):
        for rec in self:
            rec.is_pos_method = rec.payment_method_line_id.payment_method_id.code in ['pos', 'pos_manual']
            rec.is_pos_manual = rec.payment_method_line_id.payment_method_id.code == 'pos_manual'
