# -*- coding: utf-8 -*-
import json
from odoo import models, api, fields, _


class MultiInvoicePaymentWizard(models.TransientModel):
    _inherit = 'multi.invoice.payment.wizard'

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

    def action_generate_payments(self):
        res = super().action_generate_payments()
        if self._context.get('source_session_id'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sesión de Caja',
                'res_model': 'cash.management.session',
                'res_id': self._context.get('source_session_id'),
                'view_mode': 'form',
                'target': 'main',
            }
        return res


class MultiInvoicePaymentLine(models.TransientModel):
    _inherit = 'multi.invoice.payment.line'

    @api.depends('move_type', 'company_id', 'currency_id')
    def _compute_journal_id_domain(self):
        source_session_id = self._context.get('source_session_id')
        if source_session_id:
            session = self.env['cash.management.session'].browse(source_session_id)
            journal_ids, payment_method_ids = session._get_configured_journal_and_payment_methods('in')
            domain = [('id', 'in', journal_ids)]
            for rec in self:
                rec.journal_id_domain = json.dumps(domain)
        else:
            super()._compute_journal_id_domain()

    @api.depends("journal_id")
    def _compute_available_payment_method_line_ids(self):
        source_session_id = self._context.get('source_session_id')
        if source_session_id:
            session = self.env['cash.management.session'].browse(source_session_id)
            for rec in self:
                if rec.journal_id:
                    payment_method_ids = session.config_id.payment_method_id.filtered(
                        lambda pm: pm.journal_id.id == rec.journal_id.id).mapped('payment_method_in_id')
                    rec.available_payment_method_line_ids = payment_method_ids
                else:
                    rec.available_payment_method_line_ids = False
        else:
            super()._compute_available_payment_method_line_ids()
