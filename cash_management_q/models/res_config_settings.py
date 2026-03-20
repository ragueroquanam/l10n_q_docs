# -*- coding: utf-8 -*-

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cash_management_q_payment_method_ids = fields.Many2many(
        'cash.management.payment.method',
        string='Métodos de pago',
        help="Métodos de pago que se pueden usar en el punto de venta",
        related='company_id.cash_management_q_payment_method_ids',
        readonly=False
    )
    cash_management_q_cash_transfer_account_id = fields.Many2one(
        'account.account',
        string='Cuenta transferencia entre cajas',
        related='company_id.cash_management_q_cash_transfer_account_id',
        default_model='res.company',
        domain=[('deprecated', '=', False)],
        readonly=False,
        help="Cuenta contable usada para registrar transferencias internas entre cajas."
    )

    cash_management_q_surplus_account_id = fields.Many2one(
        'account.account',
        string='Cuenta predeterminada Sobrante',
        related='company_id.cash_management_q_surplus_account_id',
        default_model='res.company',
        domain="[('deprecated', '=', False)]",
        readonly=False,
        help="Cuenta contable que se usará automáticamente cuando haya un sobrante de caja."
    )

    cash_management_q_shortage_account_id = fields.Many2one(
        'account.account',
        string='Cuenta predeterminada Faltante',
        related='company_id.cash_management_q_shortage_account_id',
        default_model='res.company',
        domain="[('deprecated', '=', False)]",
        readonly=False,
        help="Cuenta contable que se usará automáticamente cuando haya un faltante de caja."
    )

    cash_management_q_move_autovalidation = fields.Boolean(
        'Validar asientos automáticamente',
        related='company_id.cash_management_q_move_autovalidation',
        readonly=False
    )
    cash_management_q_diff_move_atclose = fields.Boolean(
        'Generar asientos al cierre',
        related='company_id.cash_management_q_diff_move_atclose',
        readonly=False
    )
    cash_management_q_max_missing_amount = fields.Float(
        string='Monto tope para faltante',
        related='company_id.cash_management_q_max_missing_amount',
        readonly=False,
        help="Si la diferencia al cierre supera este monto negativo, no se permite cerrar la caja."
    )
    cash_management_q_max_over_amount = fields.Float(
        string='Monto tope para sobrante',
        related='company_id.cash_management_q_max_over_amount',
        readonly=False,
        help="Si la diferencia al cierre supera este monto positivo, no se permite cerrar la caja."
    )
