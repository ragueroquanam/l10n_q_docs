# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_credit = fields.Boolean(string='Crédito', default=False)
    pos_payment_terminal_id = fields.Many2one(comodel_name='pos.payment.terminal', string='Terminal de Pago POS')
    installment_qty = fields.Integer(string='Cuotas', default=1)
    taxable_amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,
                                     compute='_compute_taxable_amount')
    invoice_amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,
                                     compute='_compute_taxable_amount')
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
    ], string='Estado de la Transacción', default='not_start')
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

    @api.depends('can_edit_wizard', 'amount')
    def _compute_taxable_amount(self):
        # TODO OJO revisar con yoannis porque un compute tienen esto por contexto OJO
        if self._context.get('active_model') == 'account.move':
            invoices = self.env['account.move'].browse(self._context.get('active_ids', []))
        elif self._context.get('active_model') == 'account.move.line':
            move_lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
            invoices = move_lines.mapped('move_id')
        else:
            invoices = self.env['account.move']
        # active_ids = self.env.context.get('active_ids', [])
        # move_lines = self.env['account.move.line'].browse(active_ids)

        # Obtener las facturas únicas asociadas a esas líneas
        # invoices = move_lines.mapped('move_id')

        total_taxable = sum(invoices.mapped('taxable_amount'))
        total_invoice = sum(invoices.mapped('amount_total'))
        for rec in self:
            rec.taxable_amount = total_taxable
            rec.invoice_amount = total_invoice

    @api.depends('payment_method_line_id.payment_method_id.code')
    def _compute_is_pos_method(self):
        for rec in self:
            rec.is_pos_method = rec.payment_method_line_id.payment_method_id.code in ['pos', 'pos_manual']
            rec.is_pos_manual = rec.payment_method_line_id.payment_method_id.code == 'pos_manual'

    @api.constrains('installment_qty')
    def _check_installment_qty_required(self):
        for record in self:
            if record.is_credit and not record.installment_qty:
                raise ValidationError(_("Debe especificar el número de cuotas si el pago es a crédito."))

    @api.constrains('pos_invoice_number')
    def _check_pos_invoice_number_length(self):
        for record in self:
            if record.pos_invoice_number and len(record.pos_invoice_number) > 7:
                raise ValidationError('El campo "Nro Factura" no puede tener más de 7 caracteres.')

    @api.constrains('installment_qty')
    def _check_installment_qty(self):
        for rec in self:
            if rec.is_credit and not rec.installment_qty:
                raise ValidationError(_("Debe especificar el número de cuotas si el pago es a crédito."))
            if rec.installment_qty < 1:
                raise ValidationError(_("La cantidad de cuotas debe ser un número entero positivo mayor o igual a 1."))

    @api.constrains('partial_amount')
    def _check_partial_amount(self):
        for rec in self:
            if rec.is_partial_payment and (not rec.partial_amount or rec.partial_amount <= 0):
                raise ValidationError(_("Debe especificar un importe a pagar mayor a 0 si el pago es parcial."))

    @api.onchange('payment_method_line_id')
    def _onchange_payment_method_id(self):
        if self.payment_method_line_id.payment_method_id.code in ('pos', 'pos_manual') and self.communication and len(
                self.communication) >= 7:
            candidate = self.communication[-7:]
            if candidate.isdigit():
                self.pos_invoice_number = candidate

        if self.payment_method_line_id.payment_method_id.code == 'pos':
            self.transaction_number = ''
            self.transaction_state = 'not_start'
            self.tax_refund = "1" if self.vat_refund_applicable else "0"
        else:
            self.is_credit = False
            self.installment_qty = 1
            self.transaction_number = ''
            self.transaction_state = False

    @api.onchange('is_partial_payment')
    def _onchange_is_partial_payment(self):
        if not self.is_partial_payment:
            self.partial_amount = 0.0

    def _add_extra_payment_vals(self, payment_vals):
        self.tax_refund = "1" if self.vat_refund_applicable else "0"
        extra_fields = [
            'is_credit', 'pos_payment_terminal_id', 'installment_qty', 'transaction_number',
            'is_partial_payment', 'partial_amount', 'pos_invoice_number', 'ticket',
            'authorization_code', 'card_number', 'acquirer', 'transaction_state', 'transaction_date_str',
            'taxable_amount', 'pos_discount_enabled', 'tax_refund', 'payment_datetime', 'invoice_amount', 'batch_number'
        ]
        for field in extra_fields:
            value = getattr(self, field, False)
            if isinstance(self._fields[field], fields.Many2one):
                value = value.id if value else False
            payment_vals[field] = value
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        return self._add_extra_payment_vals(payment_vals)

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        return self._add_extra_payment_vals(payment_vals)
