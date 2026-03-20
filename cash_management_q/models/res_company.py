# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    cash_management_q_cash_transfer_account_id = fields.Many2one('account.account', string='Cuenta transferencia entre cajas')
    cash_management_q_surplus_account_id = fields.Many2one('account.account', string='Cuenta para Sobrante')
    cash_management_q_shortage_account_id = fields.Many2one('account.account', string='Cuenta para Faltante')
    cash_management_q_move_autovalidation = fields.Boolean('Validar asientos automáticamente')
    cash_management_q_diff_move_atclose = fields.Boolean('Generar asientos al cierre')
    cash_management_q_payment_method_ids = fields.Many2many(
        'cash.management.payment.method',
        string='Métodos de pago',
        help="Métodos de pago que se pueden usar en el punto de venta"
    )
    cash_management_q_max_missing_amount = fields.Float(
        string='Monto tope para faltante',
        help="Si la diferencia al cierre supera este monto negativo, no se permite cerrar la caja."
    )
    cash_management_q_max_over_amount = fields.Float(
        string='Monto tope para sobrante',
        help="Si la diferencia al cierre supera este monto positivo, no se permite cerrar la caja."
    )
