# -*- coding: utf-8 -*-

from odoo import models, fields


class PosTransaction(models.Model):
    _name = 'pos.transaction'
    _description = 'POS Transaction'
    _order = 'transaction_date desc'

    transaction_number = fields.Char(string='Transaction Number', required=True)
    pos_payment_terminal_id = fields.Many2one(comodel_name='pos.payment.terminal', string='Terminal de Pago POS',
                                              required=True)
    operation_type = fields.Selection(
        selection=[
            ('sale', 'Venta'),
            ('cancel', 'Anulación'),
            ('refund', 'Devolución'),
        ],
        string='Tipo de Operación',
        required=True
    )
    request_data = fields.Text(string='Datos de la Solicitud', required=True)
    transaction_date = fields.Datetime(
        string='Fecha de Transacción',
        required=True,
        default=fields.Datetime.now
    )
    got_response = fields.Boolean(string='¿Recibió Respuesta?', default=False)
    is_reversed = fields.Boolean(string='¿Revertida?', default=False)
    response_text = fields.Text(string='Texto de Respuesta')
