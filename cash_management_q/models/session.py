# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero


class CashManagement(models.Model):
    _name = "cash.management.session"
    _description = "Sesión de Caja"
    _inherit = ['mail.thread']

    name = fields.Char("Sesión", required=True, default='/')
    company_id = fields.Many2one('res.company', string='Empresa', required=True, default=lambda self: self.env.company)
    config_id = fields.Many2one('cash.management.config', string='Caja', required=True, )
    currency_id = fields.Many2one('res.currency', string='Moneda')
    date_open = fields.Datetime("Fecha de apertura", required=True, default=fields.Datetime.now)
    date_close = fields.Datetime("Fecha de cierre")
    opening_notes = fields.Text(string="Nota de apertura")
    closing_notes = fields.Text(string="Nota de cierre")
    state = fields.Selection([
        ('opened', 'En progreso'),
        ('closed', 'Cerrado'),
        ('approved', 'Aprobado'),
    ], string="Estado", default='opened', required=True, tracking=True)

    user_id = fields.Many2one(
        'res.users', string='Abierta por',
        required=True,
        index=True,
        default=lambda self: self.env.uid,
        ondelete='restrict')
    is_editable = fields.Boolean(
        string="¿Editable por el usuario?",
        compute="_compute_is_editable"
    )

    balance_start = fields.Monetary(string="Saldo de apertura", readonly=True)
    balance_end_real = fields.Monetary(string="Saldo de cierre real efectivo")
    balance_end = fields.Monetary(string="Saldo de cierre teórico efectivo", compute='_compute_balance', store=True,
                                  help="Saldo de cierre teórico calculado a partir de los movimientos de la sesión.")
    difference = fields.Monetary(string='Diferencia al cierre', compute='_compute_difference', store=True,
                                 help="Difference between the theoretical closing amount and the real closing balance.")
    balance_real_confirmed = fields.Boolean(
        string="Confirmación de saldo real",
        help="El cajero debe confirmar que revisó el saldo de cierre real efectivo antes de cerrar la caja."
    )

    balance_start_doc_to_pay = fields.Monetary(string="Saldo de apertura")
    new_doc_to_pay = fields.Monetary(string="Nuevos cheques")
    balance_end_r_doc_to_pay = fields.Monetary(string="Saldo de cierre real cheques")
    balance_end_doc_to_pay = fields.Monetary(string="Saldo de cierre teórico cheques",
                                             compute='_compute_balance_doc_to_pay',
                                             store=True,
                                             help="Saldo de cierre teórico calculado a partir de los movimientos de la sesión.")
    difference_doc_to_pay = fields.Monetary(string='Diferencia al cierre', compute='_compute_balance_doc_to_pay',
                                            store=True)

    bill_ids = fields.One2many('cash.management.session.bill.line', 'session_id', string='Monedas/Billetes')
    journal_entry_id = fields.Many2one('account.move', string='Asiento de cierre', ondelete='set null')
    incoming_payment_count = fields.Integer(string="Doc. a cobrar", compute='_compute_payment_counts')
    outgoing_payment_count = fields.Integer(string="Doc. a pagar", compute='_compute_payment_counts')

    incoming_payment_ids = fields.One2many(
        'account.payment',
        'session_id',
        string="Documentos a cobrar",
        domain=[('payment_type', '=', 'inbound')]
    )

    outgoing_payment_ids = fields.One2many(
        'account.payment',
        'session_id',
        string="Documentos a pagar",
        domain=[('payment_type', '=', 'outbound')]
    )

    cheque_payment_ids = fields.One2many(
        'account.payment',
        'session_id',
        string="Cheques entregados/recibidos",
        domain=[('journal_id.type', '=', 'bank'), ('payment_method_line_id.is_check', '=', True)]
    )

    cash_payment_ids = fields.One2many(
        'account.payment',
        'session_id',
        string="Pagos en efectivo",
        domain=[('journal_id.type', '=', 'cash')]
    )

    card_payment_ids = fields.One2many(
        'account.payment',
        'session_id',
        string="Pagos con tarjeta",
        domain=[('payment_method_line_id.payment_method_id.code', 'in', ('pos', 'pos_manual'))]
    )

    statement_line_ids = fields.One2many(
        'account.bank.statement.line',
        'session_id',
        string="Otras transacciones"
    )

    summary_line_ids = fields.One2many(
        'cash.management.session.summary.line',
        'session_id',
        string="Totales por Diario"
    )

    fund_transfer_ids = fields.One2many(
        'cash.fund.transfer',
        'session_id',
        string='Transferencias de Fondos'
    )
    has_other_currency_session = fields.Boolean(
        string="¿Tiene sesión en otra moneda?",
        compute="_compute_has_other_currency_session"
    )

    def _compute_has_other_currency_session(self):
        for rec in self:
            domain = [
                ('company_id', '=', rec.company_id.id),
                ('currency_id', '!=', rec.currency_id.id),
                ('state', '=', 'opened'),
            ]
            company_currency = rec.company_id.currency_id
            if not rec.currency_id or rec.currency_id.id == company_currency.id:
                domain.append(('config_id', 'child_of', rec.config_id.id))
            else:
                domain.append(('config_id', 'parent_of', rec.config_id.id))

            other_session = self.search_count(domain)
            rec.has_other_currency_session = bool(other_session)

    def _get_last_session(self):
        return self.env['cash.management.session'].search(
            [
                ('config_id', '=', self.config_id.id),
                ('state', 'in', ('closed', 'approved')),
            ],
            order='date_close desc',
            limit=1
        )

    def _compute_summary_lines(self):
        SummaryLine = self.env['cash.management.session.summary.line'].sudo()
        for session in self:
            summary = {}
            # --- Last session map (concept -> final_balance) ---
            last_session = session._get_last_session()
            dict_last_summary_line = (
                {line.concept: line.final_balance for line in last_session.summary_line_ids if not line.is_pos}
                if last_session else {}
            )

            # --- Helper to ensure a concept entry exists in summary ---
            def ensure(concept, is_pos=False):
                if concept not in summary:
                    summary[concept] = {
                        'concept': concept,
                        'is_pos': is_pos,
                        'initial_balance': dict_last_summary_line.get(concept, 0.0),
                        'total_in': 0.0,
                        'total_out': 0.0,
                        'transfer_in': 0.0,
                        'transfer_out': 0.0,
                    }
                return summary[concept]

            # =========================
            # CARGAR SALDOS INICIALES
            # =========================
            for k, v in dict_last_summary_line.items():
                ensure(k)

            last_session = session._get_last_session()
            dict_last_summary_line = {line.concept: line.final_balance for line in last_session.summary_line_ids if
                                      not line.is_pos}

            # =========================
            # PAGOS NORMALES (sin cheques)
            # =========================
            all_payments = (session.incoming_payment_ids + session.outgoing_payment_ids) - session.cheque_payment_ids
            for payment in all_payments:
                journal_type = payment.payment_method_line_id.name or payment.journal_id.display_name
                is_pos = payment.payment_method_line_id.payment_method_id.code in ('pos', 'pos_manual')
                line = ensure(journal_type, is_pos)
                if payment.payment_type == 'inbound':
                    line['total_in'] += payment.amount
                else:
                    line['total_out'] += payment.amount

            # =========================
            # CHEQUES (entrada/salida)
            # =========================
            cheques_in = session.cheque_payment_ids.filtered(lambda p: p.payment_type == 'inbound')
            if cheques_in:
                concept_in = "Cheques cobrados"
                line = ensure(concept_in)
                line['total_in'] += sum(cheques_in.mapped('amount'))

            cheques_out = session.cheque_payment_ids.filtered(lambda p: p.payment_type == 'outbound')
            if cheques_out or session.new_doc_to_pay:
                concept_out = "Cheques pagados"
                line = ensure(concept_out)
                line['total_in'] += float(session.new_doc_to_pay or 0.0)
                line['total_out'] += sum(cheques_out.mapped('amount'))

            # =========================
            # TRANSFERENCIAS DE FONDOS
            # =========================
            for transfer in session.fund_transfer_ids:
                concept = "Efectivo" if transfer.is_cash else "Cheques cobrados"
                line = ensure(concept)
                if transfer.type == 'income':
                    line['transfer_in'] += transfer.amount
                elif transfer.type == 'expense':
                    line['transfer_out'] += transfer.amount

            # =========================
            # Ajuste de efectivo en el cierre de caja
            # =========================
            if session.difference > 0:
                line = ensure("Efectivo")
                line['total_in'] += session.difference

            if session.difference < 0:
                line = ensure("Efectivo")
                line['total_out'] += abs(session.difference)

            # =========================
            # OTRAS TRANSACCIONES
            # =========================
            if session.statement_line_ids:
                amounts = session.statement_line_ids.mapped('amount')
                total_in = sum(a for a in amounts if a > 0) or 0.0
                total_out = abs(sum(a for a in amounts if a < 0)) or 0.0
                if total_in or total_out:
                    line = ensure("Efectivo")
                    line['total_in'] += total_in
                    line['total_out'] += total_out

            # =========================
            # Limpiar y regenerar (batch create)
            # =========================
            session.summary_line_ids.sudo().unlink()
            if summary:
                SummaryLine.create([
                    {
                        'session_id': session.id,
                        'concept': vals['concept'],
                        'is_pos': vals['is_pos'],
                        'initial_balance': vals['initial_balance'],
                        'total_in': vals['total_in'],
                        'total_out': vals['total_out'],
                        'transfer_in': vals['transfer_in'],
                        'transfer_out': vals['transfer_out'],
                    }
                    for vals in summary.values()
                ])

    @api.depends('statement_line_ids', 'incoming_payment_ids', 'outgoing_payment_ids', 'cheque_payment_ids',
                 'config_id', 'balance_start', 'fund_transfer_ids')
    def _compute_balance(self):
        for session in self:
            fund_transfer_in = sum(session.fund_transfer_ids.filtered(lambda o: o.type == 'income' and
                                                                                (
                                                                                        o.origin_payment_method_id.journal_id.type == 'cash' or (
                                                                                        o.origin_payment_method_id.journal_id.type == 'bank' and
                                                                                        o.origin_payment_method_id.type == 'common'))).mapped(
                'amount'))
            fund_transfer_out = sum(session.fund_transfer_ids.filtered(lambda o: o.type == 'expense' and
                                                                                 (
                                                                                         o.origin_payment_method_id.journal_id.type == 'cash' or (
                                                                                         o.origin_payment_method_id.journal_id.type == 'bank' and
                                                                                         o.origin_payment_method_id.type == 'common'))).mapped(
                'amount'))

            incoming_payments = session.incoming_payment_ids.filtered(lambda p: p.journal_id.type == 'cash' or (
                    p.journal_id.type == 'bank' and p.payment_method_line_id.type == 'common'))
            outgoing_payments = session.outgoing_payment_ids.filtered(lambda p: p.journal_id.type == 'cash')

            total_payment = (fund_transfer_in + sum(session.statement_line_ids.mapped('amount')) +
                             sum(incoming_payments.mapped('amount')) - fund_transfer_out -
                             sum(outgoing_payments.mapped('amount')))
            session.balance_end = session.balance_start + total_payment
            session.balance_end_real = session.balance_end
            session.difference = 0

    @api.depends('balance_end_real')
    def _compute_difference(self):
        for session in self:
            session.difference = session.balance_end_real - session.balance_end

    @api.depends('new_doc_to_pay', 'outgoing_payment_ids', 'balance_start_doc_to_pay', 'balance_end_r_doc_to_pay',
                 'balance_end_doc_to_pay')
    def _compute_balance_doc_to_pay(self):
        for session in self:
            # aqui filtrar los cheques pagados
            balance_doc_pay = sum(
                session.cheque_payment_ids.filtered(lambda o: o.payment_type == 'outbound').mapped('amount'))

            session.balance_end_doc_to_pay = session.balance_start_doc_to_pay + session.new_doc_to_pay - balance_doc_pay
            session.difference_doc_to_pay = session.balance_end_r_doc_to_pay - session.balance_end_doc_to_pay

    def _compute_is_editable(self):
        current_user = self.env.user
        for session in self:
            session.is_editable = session.state == 'opened' and session.user_id.id == current_user.id

    def write(self, vals):
        res = super().write(vals)
        # Si alguno de los campos objetivo cambió, recalcular totales
        trigger_fields = {'balance_end_real', 'new_doc_to_pay'}
        if trigger_fields.intersection(vals.keys()):
            self._compute_summary_lines()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('cash.management.session') or _('Nuevo')
        res = super().create(vals_list)
        return res

    def _create_adjustment_move(self):
        journal = self.config_id.journal_id  # Diario configurado en la caja
        if not journal:
            raise UserError(_("No hay diario configurado en la caja"))
        cash_account = journal.default_account_id
        if not cash_account:
            raise UserError(_("No hay cuenta de efectivo configurada en el diario de la caja."))

        cash_management_q_surplus_account_id = self.company_id.cash_management_q_surplus_account_id
        if self.difference > 0 and not cash_management_q_surplus_account_id:
            raise UserError(
                _("No hay cuenta de Sobrante de caja configurada en la empresa. Ir a los Ajustes y configurar el campo 'Sobrante de caja'."))

        cash_management_q_shortage_account_id = self.company_id.cash_management_q_shortage_account_id
        if self.difference < 0 and not cash_management_q_shortage_account_id:
            raise UserError(
                _("No hay cuenta de Faltante de caja configurada en la empresa. Ir a los Ajustes y configurar el campo 'Faltante de caja'."))

        debit_account = None
        credit_account = None
        if self.difference > 0:
            debit_account = cash_account
            credit_account = cash_management_q_surplus_account_id if cash_management_q_surplus_account_id else False
            currency_id = cash_account.currency_id
            debit_amount_currency = abs(self.difference)
            credit_amount_currency = debit_amount_currency * -1
        elif self.difference < 0:
            debit_account = cash_management_q_shortage_account_id if cash_management_q_shortage_account_id else False
            credit_account = cash_account
            currency_id = cash_account.currency_id
            debit_amount_currency = abs(self.difference)
            credit_amount_currency = debit_amount_currency * -1
        if currency_id != self.env.company.currency_id:
            amount = currency_id._convert(abs(self.difference), self.env.company.currency_id, self.company_id,
                                          fields.Date.context_today(self))
        else:
            amount = abs(self.difference)

        if debit_account and credit_account:
            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'session_id': self.id,
                'date': fields.Date.context_today(self),
                'ref': f"Cierre caja {self.name}",
                'line_ids': [
                    (0, 0, {
                        'name': 'Ajuste caja',
                        'account_id': debit_account.id,
                        'debit': amount,
                        'amount_currency': debit_amount_currency,
                        'credit': 0.0,
                        'currency_id': self.currency_id.id,
                    }),
                    (0, 0, {
                        'name': 'Ajuste caja',
                        'account_id': credit_account.id,
                        'debit': 0.0,
                        'credit': amount,
                        'amount_currency': credit_amount_currency,
                        'currency_id': self.currency_id.id,
                    }),
                ]
            })
            move.action_post()
            return move
        return None

    def _create_statement_line_moves(self):
        journal = self.config_id.payment_method_id.journal_id  # Diario configurado en la caja
        if not journal:
            raise UserError(_("No hay diario configurado en la caja"))

        if not journal.cash_in_account_id or not journal.cash_out_account_id:
            raise UserError(_("Configure las cuentas para Caja Chica en el diario"))

        for line in self.statement_line_ids:
            if line.amount == 0:
                continue
            default_account_id = line.account_id
            if not default_account_id:
                raise UserError(_("No se encontró una cuenta configurada en la transacción"))

            ref = f"Transaccion {line.name} de la sesion {self.name}."
            amount = abs(line.amount)

            if line.amount > 0:
                debit_account = journal.cash_in_account_id.id
                credit_account = default_account_id.id
                amount_currency_credit = -amount
            else:
                debit_account = default_account_id.id
                credit_account = journal.cash_out_account_id.id
                amount_currency_credit = line.amount  # negativo

            line_ids = [
                (0, 0, {
                    'name': ref,
                    'account_id': debit_account,
                    'debit': amount,
                    'credit': float(0),
                    'amount_currency': amount,
                }),
                (0, 0, {
                    'name': ref,
                    'account_id': credit_account,
                    'debit': float(0),
                    'credit': amount,
                    'amount_currency': amount_currency_credit,
                }),
            ]

            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'session_id': self.id,
                'date': fields.Date.context_today(self),
                'ref': ref,
                'line_ids': line_ids
            })
            move.action_post()
            line.journal_entry_id = move.id

    def action_close_session(self):
        for rec in self:
            # Validación del check
            if not rec.balance_real_confirmed:
                raise ValidationError(
                    _("Debe marcar la casilla de confirmación para verificar el campo 'Saldo de cierre real efectivo' antes de cerrar la caja."))

            if not float_is_zero(rec.difference_doc_to_pay, precision_digits=2):
                raise ValidationError(_(
                    "No se puede cerrar la sesión porque hay una diferencia de %.2f en el arqueo de cheques a pagar.\n\n"
                    "Verifique los siguientes campos en la sección 'ARQUEO CHEQUES A PAGAR':\n"
                    "- Saldo de cierre teórico cheques\n"
                    "- Saldo de cierre real cheques\n\n"
                    "Para cerrar la sesión, estas cantidades deben coincidir y la diferencia debe ser 0."
                ) % rec.difference_doc_to_pay)

            max_missing = rec.company_id.cash_management_q_max_missing_amount or 0.0
            max_over = rec.company_id.cash_management_q_max_over_amount or 0.0
            diff = rec.difference

            if max_missing and diff < 0 and abs(diff) > max_missing:
                raise ValidationError(_("No se puede cerrar la caja: el faltante supera el monto permitido."))
            if max_over and diff > 0 and diff > max_over:
                raise ValidationError(_("No se puede cerrar la caja: el sobrante supera el monto permitido."))

            rec.write({"state": 'closed', 'date_close': fields.Datetime.now()})
            # Generar asientos segun las lineas en la pestaña otras trancciones
            # todo de momento no hacer esto
            # rec._create_statement_line_moves()

            # Generar asiento contable de ajuste de caja
            if diff:
                move = rec._create_adjustment_move()
                rec.journal_entry_id = move.id

    def action_approve_session(self):
        self.write({'state': 'approved'})

    def reverse_journal_entry(self, move):
        if move and move.state != 'cancel':
            move.button_draft()
            move.button_cancel()
            move.unlink()

    def action_cancel_session(self):
        for rec in self:
            # Verificar si hay otra sesión posterior para la misma caja
            newer_session = self.search([
                ('company_id', '=', rec.company_id.id),
                ('config_id', '=', rec.config_id.id),
                ('date_open', '>', rec.date_open),
                ('id', '!=', rec.id)
            ], limit=1)
            if newer_session:
                raise ValidationError(_(
                    "No se puede cancelar esta sesión porque existe una sesión posterior para la misma caja "
                    f"({newer_session.name}) con fecha de apertura {newer_session.date_open.strftime('%d/%m/%Y %H:%M')}."
                ))

            rec.state = 'opened'

            # Extornar asiento contable de ajuste de caja
            if rec.journal_entry_id:
                self.reverse_journal_entry(rec.journal_entry_id)
                rec.journal_entry_id = False

    @api.depends('incoming_payment_ids', 'outgoing_payment_ids')
    def _compute_payment_counts(self):
        for rec in self:
            rec.incoming_payment_count = self.env['account.move'].search_count([
                ('move_type', 'in', ['out_invoice', 'out_refund', 'out_receipt']),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('company_id', '=', rec.company_id.id)
            ])
            journal_ids, payment_method_ids = rec._get_configured_journal_and_payment_methods('out')
            rec.outgoing_payment_count = self.env['account.payment'].search_count([
                ('state', '=', 'to approve'),
                ('company_id', '=', self.company_id.id),
                ('journal_id', 'in', journal_ids),
                ('payment_method_line_id', 'in', payment_method_ids),
            ])

    def action_view_incoming_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documentos a Cobrar',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('account.view_out_invoice_tree').id, 'list'),
                (self.env.ref('account.view_move_form').id, 'form'),
            ],
            'search_view_id': self.env.ref('account.view_account_invoice_filter').id,
            'domain': [('move_type', 'in', ['out_invoice', 'out_receipt']), ('state', '=', 'posted'),
                       ('payment_state', 'in', ('not_paid', 'partial')), ('company_id', '=', self.company_id.id)],
            'context': {'create': False, 'default_move_type': 'out_invoice', 'source_session_id': self.id},
        }

    def _get_configured_journal_and_payment_methods(self, payment_methods_type):
        self.ensure_one()

        # Obtener métodos de pago salientes configurados para esos diarios
        if payment_methods_type == 'in':
            payment_method_records = self.config_id.payment_method_id.mapped('payment_method_in_id')
        else:
            payment_method_records = self.config_id.payment_method_id.mapped('payment_method_out_id')

        # Filtrar diarios para los que existan métodos de pago
        journal_ids = payment_method_records.mapped('journal_id').ids

        return journal_ids, payment_method_records.ids

    def action_view_outgoing_payments(self):
        self.ensure_one()
        journal_ids, payment_method_ids = self._get_configured_journal_and_payment_methods('out')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documentos a Pagar',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [
                ('state', '=', 'to approve'),
                ('company_id', '=', self.company_id.id),
                ('journal_id', 'in', journal_ids),
                ('payment_method_line_id', 'in', payment_method_ids),
            ],
            'context': {'default_payment_type': 'outbound', 'default_partner_type': 'supplier',
                        'search_default_outbound_filter': 1, 'default_move_journal_types': ('bank', 'cash'),
                        'display_account_trust': True, 'source_session_id': self.id},
        }

    def action_open_other_currency_session(self):
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('currency_id', '!=', self.currency_id.id),
            ('state', '=', 'opened'),
        ]
        company_currency = self.company_id.currency_id
        if not self.currency_id or self.currency_id.id == company_currency.id:
            domain.append(('config_id', 'child_of', self.config_id.id))
        else:
            domain.append(('config_id', 'parent_of', self.config_id.id))

        other_session = self.search(domain, limit=1)

        if not other_session:
            raise UserError("No hay otra sesión abierta en una moneda diferente para esta misma compañía.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sesión de Caja',
            'res_model': 'cash.management.session',
            'view_mode': 'form',
            'res_id': other_session.id,
            'target': 'current',
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    session_id = fields.Many2one(
        'cash.management.session',
        string='Sesión de Caja',
        readonly=True,
        help="Sesión de caja desde la que se generó este asiento, si aplica."
    )

    def write(self, vals):
        # Administracion / Ajustes no tienen restricción
        if self.env.user.has_group('base.group_system'):
            return super().write(vals)

        # Solo si está relacionado a caja
        cash_moves = self.filtered(lambda m: m.session_id)
        if cash_moves:
            # Solo controlar cuando viene desde el menú de asientos contables
            if self.env.context.get('from_account_move_menu'):
                raise UserError(_(
                    "No está permitido modificar asientos contables "
                    "asociados a una caja desde el menú de Asientos Contables."
                ))

            protected_fields = {'line_ids', 'journal_id', 'partner_id', 'amount_total'}
            # Controlar que no se modifique el asiento si tiene pagos asociados
            if protected_fields.intersection(vals.keys()) and self.origin_payment_id and self.origin_payment_id.state != 'draft':
                raise UserError(_(
                    "No está permitido modificar asientos contables que tengan pagos registrados "
                    "asociados a una caja."
                ))

        return super().write(vals)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    session_id = fields.Many2one(
        'cash.management.session',
        related='move_id.session_id',
        string='Sesión de Caja',
        store=True,
        readonly=True
    )

    def action_register_payment(self):
        res = super().action_register_payment()
        source_session_id = self.env.context.get('source_session_id', False)
        if not source_session_id:
            return res
        if 'context' in res:
            res['context'].update({'source_session_id': source_session_id})
        else:
            res['context'] = {'source_session_id': source_session_id}
        return res


class CashManagementOpeningControlLine(models.Model):
    _name = 'cash.management.session.bill.line'
    _description = 'Línea de Monedas/Billetes de la Sesión'

    session_id = fields.Many2one('cash.management.session', string='Sesión', required=True, index=True)
    config_id = fields.Many2one(
        'cash.management.config',
        string='Caja',
        related='session_id.config_id',
        store=True,
        index=True,
    )
    bill_id = fields.Many2one(
        'cash.management.bill',
        string='Moneda/Billete',
        required=True,
        domain="['|',('is_for_all_config', '=', True), ('config_ids', '=', config_id)]")
    value = fields.Float("Valor de la moneda", related='bill_id.value', digits=(16, 4))
    quantity = fields.Float("Cantidad", required=True)


class CashManagementSummaryLine(models.Model):
    _name = "cash.management.session.summary.line"
    _description = "Detalle de Totales por Diario"
    _order = "concept"

    session_id = fields.Many2one('cash.management.session', string="Sesión de Caja", ondelete='cascade', required=True)
    concept = fields.Char(string="Concepto", required=True)
    is_pos = fields.Boolean(string="Es POS", required=False, default=False)
    initial_balance = fields.Monetary(string="Saldo Inicial", currency_field='currency_id')
    transfer_in = fields.Monetary(string="Transf. entrantes", currency_field='currency_id')
    transfer_out = fields.Monetary(string="Transf. salientes", currency_field='currency_id')
    total_in = fields.Monetary(string="Entradas", currency_field='currency_id')
    total_out = fields.Monetary(string="Salidas", currency_field='currency_id')
    final_balance = fields.Monetary(string="Saldo Final", compute='_compute_final_balance', store=True)
    currency_id = fields.Many2one(related='session_id.currency_id', store=True, readonly=True)

    @api.depends('initial_balance', 'total_in', 'total_out', 'transfer_in', 'transfer_out')
    def _compute_final_balance(self):
        for line in self:
            line.final_balance = (line.initial_balance or 0) + (line.total_in or 0) + (line.transfer_in or 0) - (
                    line.total_out or 0) - (line.transfer_out or 0)
