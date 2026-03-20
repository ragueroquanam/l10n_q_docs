# -*- coding: utf-8 -*-

import json
from odoo import models, fields, api, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError, ValidationError


class CashFundTransfer(models.Model):
    _name = 'cash.fund.transfer'
    _description = 'Transferencia de Fondos'

    session_id = fields.Many2one('cash.management.session', string='Sesión', required=False, ondelete='cascade')
    config_id = fields.Many2one('cash.management.config', string='Caja', related="session_id.config_id", store=True,
                                readonly=True)
    date = fields.Date(string='Fecha', required=True, default=fields.Date.context_today)
    type = fields.Selection([
        ('income', 'Ingreso'),
        ('expense', 'Egreso')
    ], string='Tipo', required=True, default="expense")
    internal_transfer = fields.Selection([
        ('to_cash', 'A caja'),
        ('to_bank', 'A banco')
    ], string='Transferencia interna', required=True)
    description = fields.Char(string='Descripción')
    origin_journal_id = fields.Many2one(
        'account.journal',
        string='Diario Origen'
    )
    origin_journal_id_domain = fields.Char(
        compute='_compute_origin_journal_id_domain',
        store=False
    )
    origin_payment_method_id = fields.Many2one(
        'account.payment.method.line',
        string='Diario Origen'
    )
    origin_payment_method_id_domain = fields.Char(
        compute='_compute_origin_payment_method_id_domain',
        store=False
    )

    journal_entry_id = fields.Many2one('account.move', string='Asiento contable')
    payment_method_id = fields.Many2one('account.payment.method.line', string='Banco destino')
    destination_config_id = fields.Many2one('cash.management.config', string='Caja destino')
    destination_config_domain = fields.Char(
        compute="_compute_destination_config_domain",
        compute_sudo=True,
        store=False
    )
    bank_journal_id = fields.Many2one('account.journal', string='Banco', domain="[('type', '=', 'bank')]")
    detail = fields.Text(string='Detalle')
    amount = fields.Monetary(string='Importe', required=True)
    reason = fields.Char(string='Motivo')
    currency_id = fields.Many2one('res.currency', string='Moneda', related='session_id.currency_id', store=True,
                                  readonly=True)
    mirrored_transfer_id = fields.Many2one('cash.fund.transfer', string='Transferencia Inversa', readonly=True,
                                           copy=False)
    payment_method_id_domain = fields.Char(
        compute='_compute_payment_method_id_domain',
        store=False
    )
    is_cash = fields.Boolean(
        string='¿Es en efectivo?',
        compute='_compute_is_cash',
        store=False
    )

    @api.depends('origin_payment_method_id.journal_id.type',
                 'mirrored_transfer_id.origin_payment_method_id.journal_id.type')
    def _compute_is_cash(self):
        for rec in self:
            if rec.origin_payment_method_id:
                rec.is_cash = rec.origin_payment_method_id.journal_id.type == 'cash'
            else:
                rec.is_cash = rec.mirrored_transfer_id.origin_payment_method_id.journal_id.type == 'cash'

    @api.depends('config_id', 'config_id.cash_transfer_target_ids')
    def _compute_destination_config_domain(self):
        for rec in self:
            config = rec.config_id.sudo()
            if config and config.cash_transfer_target_ids:
                rec.destination_config_domain = json.dumps([
                    ('id', 'in', config.cash_transfer_target_ids.ids)
                ])
            else:
                rec.destination_config_domain = json.dumps([('id', '=', 0)])

    @api.depends('config_id')
    def _compute_origin_journal_id_domain(self):
        for rec in self:
            if rec.config_id.bank_transfer_journal_ids:
                method_ids = rec.config_id.bank_transfer_journal_ids.ids
                domain = [('id', 'in', method_ids)]
            else:
                domain = []
            rec.origin_journal_id_domain = json.dumps(domain)

    @api.depends('config_id')
    def _compute_origin_payment_method_id_domain(self):
        for rec in self:
            if rec.config_id.payment_method_id:
                method_ids = rec.config_id.payment_method_id.mapped('payment_method_out_id').ids
                domain = [('id', 'in', method_ids)]
            else:
                domain = []
            rec.origin_payment_method_id_domain = json.dumps(domain)

    @api.depends('config_id')
    def _compute_payment_method_id_domain(self):
        for rec in self:
            if rec.config_id and rec.config_id.bank_transfer_journal_ids:
                method_ids = rec.config_id.bank_transfer_journal_ids.inbound_payment_method_line_ids.ids
                domain = [('id', 'in', method_ids)]
            else:
                domain = [('id', '=', False)]
            rec.payment_method_id_domain = json.dumps(domain)

    @api.constrains('config_id', 'destination_config_id')
    def _check_config_ids(self):
        for rec in self:
            if rec.type == 'expense' and rec.config_id and rec.destination_config_id and rec.config_id.id == rec.destination_config_id.id:
                raise ValidationError(_('La Caja destino debe ser diferente a la Caja origen.'))

    def _get_account_from_journal_payment_method(self, payment_method):
        self.ensure_one()

        journal = payment_method.journal_id
        method_line = payment_method

        if not method_line:
            raise UserError(_('No se encontró el método de pago en el diario especificado.'))

        if not method_line.payment_account_id:
            return journal.default_account_id.id

        return method_line.payment_account_id.id

    @api.model_create_multi
    def create(self, vals_list):
        transfers = super().create(vals_list)

        for transfer in transfers:
            if transfer.type == 'expense':
                if float_is_zero(transfer.amount, precision_digits=2):
                    raise UserError(_('El importe debe ser mayor a cero.'))

                if transfer.is_cash:
                    cash_summary_line = transfer.session_id.summary_line_ids.filtered(
                        lambda line: line.concept == 'Efectivo'
                    )
                    if cash_summary_line and cash_summary_line[0].final_balance < transfer.amount:
                        raise UserError(_('El importe debe ser menor al Saldo en efectivo de la caja.'))
                else:
                    check_summary_line = transfer.session_id.summary_line_ids.filtered(
                        lambda line: line.concept == 'Cheques cobrados'
                    )
                    if check_summary_line and check_summary_line[0].final_balance < transfer.amount:
                        raise UserError(_('El importe debe ser menor al Saldo de Cheques cobrados de la caja.'))

                # Validación de configuración mínima
                if (not transfer.config_id or not transfer.session_id):
                    raise UserError(_('Faltan datos de configuración de la caja o sesión.'))

                # Determinar diario contable
                journal = transfer.config_id.journal_id or transfer.bank_journal_id
                if not journal:
                    raise UserError(_('No se encontró un diario para generar el asiento contable.'))

                currency = transfer.currency_id or transfer.session_id.currency_id or self.env.company.currency_id

                # Crear asiento contable
                cash_management_q_cash_transfer_account_id = self.env.company.cash_management_q_cash_transfer_account_id.id
                credit_account_id = transfer.config_id.cash_transfer_account_id.id
                debit_account_id = False
                if not credit_account_id:
                    raise UserError(
                        _('No se encontró la Cuenta de transferencia entre cajas en la configuración de Caja.'))
                if not cash_management_q_cash_transfer_account_id:
                    raise UserError(
                        _('No se encontró la Cuenta Transferencia entre caja en los Ajustes del módulo de Caja.'))

                if transfer.internal_transfer == 'to_cash' and transfer.destination_config_id:
                    debit_account_id = cash_management_q_cash_transfer_account_id
                elif transfer.internal_transfer == 'to_bank':
                    debit_account_id = transfer._get_account_from_journal_payment_method(transfer.payment_method_id)
                    credit_account_id = transfer._get_account_from_journal_payment_method(
                        transfer.origin_payment_method_id)

                formatted_description = self._build_transfer_description(transfer, _('Salida transferencia de Fondos'),
                                                                         'OUT')

                move = self._create_transfer_move(
                    debit_account_id=debit_account_id,
                    credit_account_id=credit_account_id,
                    amount=transfer.amount,
                    date=transfer.date,
                    journal=journal,
                    currency=currency,
                    description=formatted_description,
                    session=transfer.session_id
                )

                # Crear transferencia inversa solo si es entre cajas
                if transfer.internal_transfer == 'to_cash' and transfer.destination_config_id:
                    inverse_transfer = self.create({
                        'session_id': None,
                        'date': transfer.date,
                        'type': 'income',
                        'internal_transfer': 'to_cash',
                        'description': transfer.description,
                        'reason': transfer.reason,
                        'detail': transfer.detail,
                        'payment_method_id': transfer.payment_method_id.id,
                        'destination_config_id': transfer.destination_config_id.id,
                        'amount': transfer.amount,
                        'bank_journal_id': False,
                        'mirrored_transfer_id': transfer.id
                    })
                    transfer.with_context(allow_cash_fund_transfer_write=True).write(
                        {'journal_entry_id': move.id, 'mirrored_transfer_id': inverse_transfer.id})
                else:
                    transfer.with_context(allow_cash_fund_transfer_write=True).write({'journal_entry_id': move.id})

        return transfers

    def write(self, vals):
        if self.env.context.get('allow_cash_fund_transfer_write'):
            return super().write(vals)
        raise UserError(_('No está permitido modificar una transferencia de fondos una vez creada.'))

    def unlink(self):
        deletable_transfers = self.browse()

        for transfer in self:
            # CASO 1: Transferencia de ENTRADA entre cajas → no eliminar
            if transfer.internal_transfer == 'to_cash' and transfer.type == 'income':
                if transfer.session_id:
                    transfer.session_id.reverse_journal_entry(transfer.journal_entry_id)

                session = transfer.session_id
                transfer.with_context(allow_cash_fund_transfer_write=True).write({
                    'session_id': None
                })
                session._compute_difference()
                continue

            # CASO 2: Validación de sesión cerrada
            if transfer.session_id and transfer.session_id.state != 'opened':
                raise UserError(
                    _('No puede eliminar una transferencia de fondos si la sesión de caja no está abierta.'))

            # CASO 3: Egreso entre cajas, pero ya recibido en destino
            if transfer.internal_transfer == 'to_cash' and transfer.type == 'expense' and transfer.mirrored_transfer_id.session_id:
                raise UserError(_('No puede eliminar esta transferencia: ya fue recibida en la caja destino.'))

            # CASO 4: Transferencia a cajas, no recibido en destino, se eliminar tambien la transferencia inversa
            if transfer.internal_transfer == 'to_cash' and transfer.type == 'expense' and transfer.mirrored_transfer_id:
                deletable_transfers |= transfer.mirrored_transfer_id

            # CASO 5: Transferencia eliminable → agregar al conjunto a eliminar
            transfer.session_id.reverse_journal_entry(transfer.journal_entry_id)
            deletable_transfers |= transfer

        sessions = deletable_transfers.mapped('session_id')
        res = super(CashFundTransfer, deletable_transfers).unlink()
        sessions._compute_difference()
        return res

    def _build_transfer_description(self, transfer, default_description, move_type):
        """
        Build a formatted description for transfer moves.
        :param transfer: record with description, reason and detail fields
        :return: formatted description string
        """
        description_parts = []

        if transfer.description:
            description_parts.append("%s - %s" % (move_type, transfer.description))
        else:
            description_parts.append(default_description)

        if transfer.reason:
            description_parts.append(_('Motivo: %s') % transfer.reason)

        if transfer.detail:
            description_parts.append(_('Detalle: %s') % transfer.detail)

        return ' | '.join(description_parts)

    def action_confirm_transfers(self):
        self.ensure_one()
        config_id = self.env.context.get('config_id')
        if not config_id:
            raise UserError(_('No se ha proporcionado una caja en el contexto.'))

        config = self.env['cash.management.config'].browse(config_id)

        session = self.env['cash.management.session'].search(
            [
                ('config_id', '=', config.id),
                ('state', '=', 'opened'),
            ],
            order='date_close desc',
            limit=1
        )

        if not session:
            raise UserError(_('No se encontró una sesión abierta para la caja especificada.'))

        cash_management_q_cash_transfer_account_id = self.env.company.cash_management_q_cash_transfer_account_id.id

        formatted_description = self._build_transfer_description(self, _('Entrada transferencia de Fondos'), 'IN')

        move = self._create_transfer_move(
            debit_account_id=config.cash_transfer_account_id.id,
            credit_account_id=cash_management_q_cash_transfer_account_id,
            amount=self.amount,
            date=self.date,
            journal=config.journal_id,
            currency=self.currency_id or session.currency_id or self.env.company.currency_id,
            description=formatted_description,
            session=session
        )

        self.with_context(allow_cash_fund_transfer_write=True).write(
            {'journal_entry_id': move.id, 'session_id': session.id})

    def _create_transfer_move(self, debit_account_id, credit_account_id, amount, date, journal, currency, description,
                              session):
        if not debit_account_id or not credit_account_id:
            raise UserError(_('No se encontraron cuentas contables en la configuración.'))

        description = description or _('Transferencia de Fondos')
        currency_id = currency.id

        company_currency = self.env.company.currency_id
        if currency and currency != company_currency:
            balance = currency._convert(amount, company_currency, self.env.company, date)
            move_lines = [
                (0, 0, {
                    'account_id': debit_account_id,
                    'name': description,
                    'debit': balance,
                    'credit': 0.0,
                    'currency_id': currency.id,
                    'amount_currency': amount,
                }),
                (0, 0, {
                    'account_id': credit_account_id,
                    'name': description,
                    'debit': 0.0,
                    'credit': balance,
                    'currency_id': currency.id,
                    'amount_currency': -amount,
                }),
            ]
        else:
            move_lines = [
                (0, 0, {
                    'account_id': debit_account_id,
                    'name': description,
                    'debit': amount,
                    'credit': 0.0,
                    'currency_id': currency.id,
                }),
                (0, 0, {
                    'account_id': credit_account_id,
                    'name': description,
                    'debit': 0.0,
                    'credit': amount,
                    'currency_id': currency.id,
                }),
            ]

        move = self.env['account.move'].create({
            'date': date,
            'journal_id': journal.id,
            'line_ids': move_lines,
            'session_id': session.id,
            'ref': description,
        })
        move.action_post()
        return move

    def action_open_move(self):
        """Abrir el asiento contable relacionado"""
        self.ensure_one()
        if not self.journal_entry_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asiento contable',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.journal_entry_id.id,
            'target': 'current',
        }
