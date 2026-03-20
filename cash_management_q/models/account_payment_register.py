# -*- coding: utf-8 -*-

import json
from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        context = self.env.context

        if 'source_session_id' in context:
            res['session_id'] = context['source_session_id']

        return res

    session_id = fields.Many2one(
        'cash.management.session',
        string="Sesión de Caja",
        help="Seleccione la sesión de caja desde la cual se realizarán los pagos.",
    )
    show_session_field = fields.Boolean(compute='_compute_show_session_field')
    session_id_domain = fields.Char(compute="_compute_session_id_domain")

    @api.depends_context('source_session_id')
    @api.depends('company_id')
    def _compute_show_session_field(self):
        context = self.env.context
        for wizard in self:
            wizard.show_session_field = 'source_session_id' in context

    @api.depends_context('source_session_id')
    @api.depends('company_id')
    def _compute_session_id_domain(self):
        CashManagementSession = self.env['cash.management.session']
        source_session_id = self.env.context.get('source_session_id', 0)
        session = CashManagementSession.browse(source_session_id)
        if not session or not session.config_id:
            domain = []
        else:
            domain = [
                ('company_id', '=', session.config_id.company_id.id),
                ('state', '=', 'opened'),
                "|",
                ('config_id', 'child_of', session.config_id.id or False),
                ('config_id', 'parent_of', session.config_id.id or False)
            ]
        for wizard in self:
            wizard.session_id_domain = json.dumps(domain)

    @api.depends('payment_type', 'company_id', 'can_edit_wizard', 'session_id')
    def _compute_available_journal_ids(self):
        for wizard in self:
            available_journals = self.env['account.journal']
            if wizard.session_id:
                session = wizard.session_id
                journal_ids, payment_method_ids = session._get_configured_journal_and_payment_methods('in')
                journals = self.env['account.journal'].browse(journal_ids)
                available_journals |= journals
            else:
                for batch in wizard.batches:
                    available_journals |= wizard._get_batch_available_journals(batch)

            wizard.available_journal_ids = [Command.set(available_journals.ids)]

    @api.depends('payment_type', 'journal_id', 'currency_id')
    def _compute_payment_method_line_fields(self):
        for wizard in self:
            wizard.available_payment_method_line_ids = wizard._get_available_payment_method_lines_from_context(
                wizard.journal_id, wizard.payment_type
            )

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_line_id(self):
        for wizard in self:
            available_payment_method_lines = wizard._get_available_payment_method_lines_from_context(
                wizard.journal_id, wizard.payment_type
            )

            if available_payment_method_lines and wizard.payment_method_line_id in available_payment_method_lines:
                continue

            # Select the first available one by default.
            if available_payment_method_lines:
                move_payment_method_lines = wizard.line_ids.move_id.preferred_payment_method_line_id
                if len(move_payment_method_lines) == 1 and move_payment_method_lines.id in available_payment_method_lines.ids:
                    wizard.payment_method_line_id = move_payment_method_lines
                else:
                    wizard.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                wizard.payment_method_line_id = False

    def _get_available_payment_method_lines_from_context(self, journal_id, payment_type):
        if journal_id:
            if self.session_id:
                session = self.session_id
                payment_method_ids = session.config_id.payment_method_id.filtered(
                    lambda pm: pm.journal_id.id == journal_id.id).mapped('payment_method_in_id')
                return payment_method_ids
            else:
                return journal_id._get_available_payment_method_lines(payment_type)
        return False

    def _compute_bank_journal_id_domain(self):
        for rec in self:
            session = False
            if rec.session_id:
                session = rec.session_id
            if session and session.config_id:
                journal_ids = session.config_id.payment_method_id.mapped('journal_id').ids
                domain = [('id', 'in', journal_ids)]
            else:
                domain = []
            rec.bank_journal_id_domain = json.dumps(domain)

    def action_create_payments(self):
        session = False
        if self.session_id:
            session = self.session_id
            if session:
                session_currency_id = session.currency_id or session.company_id.currency_id
                if session.state != 'opened':
                    raise UserError(_("La sesión de caja debe estar abierta para crear pagos."))
                if session.balance_end < self.amount and self.payment_type == 'outbound':
                    raise UserError(_("No hay suficiente saldo en la sesión de caja para realizar este pago."))
                if self.currency_id != session_currency_id:
                    raise UserError(_("La moneda del pago debe ser igual a la moneda de la sesión de caja."))

        res = super().action_create_payments()
        if session:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'cash.management.session',
                'res_id': session.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return res
