# -*- coding: utf-8 -*-

from odoo import models, fields


class StatementChangesEquityConf(models.Model):
    _name = 'statement.changes.equity.conf'
    _description = 'Evolucion Patrimonio Conf'
    _order = 'sequence'

    name = fields.Char(string=u'Rubro', size=50, required=True)
    section = fields.Selection(selection=[
        ('1', 'Saldos iniciales'),
        ('2', u'Modificación al saldo inicial'),
        ('3', 'Movimientos del ejercicio'),
        ('4', 'Saldo finales')
    ], string=u'Sección', required=True)

    type = fields.Selection(selection=[
        ('sum', 'Vista'),
        ('accounts', 'Cuentas')
    ], string=u'Tipo', default='accounts', required=True)

    sign = fields.Selection(selection=[
        ('-1', 'Invertir signo del saldo'),
        ('1', 'Preserver signo del saldo')
    ], string='Signo en informes',
        help=u'Para cuentas que tipicamente tienen más débito que crédito y que desea imprimir con importes negativos en '
             u'sus informes, debería revertir el signo en el balance;p.e: cuenta de gasto. La misma aplica para cuentas '
             u'que tipicamente tienen más crédito que débito y que desea imprimir con importes positivos en sus informes. '
             u'p.e: cuenta de ingresos.')

    parent_id = fields.Many2one(comodel_name='statement.changes.equity.conf', string='Padre',
                                domain=[('type', '=', 'sum')])
    child_ids = fields.One2many(comodel_name="statement.changes.equity.conf", inverse_name="parent_id", string="Hijos")
    sequence = fields.Integer(string='Secuencia')
    line_ids = fields.One2many(comodel_name='statement.changes.equity.conf.line', inverse_name='epp_id',
                               string='Cuentas')


class StatementChangesEquityConfLine(models.Model):
    _name = 'statement.changes.equity.conf.line'
    _description = 'Evolucion Patrimonio linea Conf'

    epp_id = fields.Many2one(comodel_name='statement.changes.equity.conf', string='EEP', required=True)
    account_id = fields.Many2one(comodel_name='account.account', string='Cuenta', required=True, copy=False)

    headers = fields.Selection(selection=[
        ('capital', 'Capital'),
        ('comp', 'Aportes y Comprom. a Capital'),
        ('adjust', 'Ajustes al patrimonio'),
        ('reserve', 'Reservas'),
        ('result', 'Resultados acumulados'),
    ], string='Columnas', copy=False, required=True)

    amount_option = fields.Selection([
        ('initial_balance', 'Saldo contable al inicio del ejercicio'),
        ('balance', 'Movimientos'),
        ('close_balance', 'Saldo contable al cierre del ejercicio')
    ], string=u'Forma de cálculo de importe', default='initial_balance', required=True)
