# -*- coding: utf-8 -*-

from odoo import models, fields


class PosTransactionLog(models.Model):
    _name = 'pos.transaction.log'
    _description = 'Log de Transacciones POS'
    _order = 'create_date desc'

    method = fields.Char(string='Método')
    endpoint = fields.Char(string='Dirección del servicio')
    request_body = fields.Text(string='Solicitud')
    response_body = fields.Text(string='Respuesta')
    state = fields.Selection([
        ('sent', 'Enviado'),
        ('success', 'Exitoso'),
        ('failed', 'Fallido')
    ], string='Estado', default='sent')
    payment_provider_id = fields.Many2one(
        comodel_name='pos.payment.provider',
        string='Proveedor de pago',
    )
