# -*- coding: utf-8 -*-

import json
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.misc import format_datetime


class CashManagement(models.Model):
    _name = "cash.management.payment.method"
    _description = "Método de pago"

    name = fields.Char("Método", required=True)
    payment_method_in_id = fields.Many2many(
        'account.payment.method.line',
        relation='cash_mgmt_payment_method_in_rel',
        string='Métodos de pago entrantes'
    )

    payment_method_out_id = fields.Many2many(
        'account.payment.method.line',
        relation='cash_mgmt_payment_method_out_rel',
        string='Métodos de pago salientes'
    )
    payment_method_in_domain = fields.Char(
        compute='_compute_payment_method_in_domain',
        store=False
    )
    payment_method_out_domain = fields.Char(
        compute='_compute_payment_method_out_domain',
        store=False
    )

    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        required=True,
        domain="[('type', 'in', ['bank', 'cash', 'credit'])]"
    )
    currency_id = fields.Many2one('res.currency', string='Moneda', required=False)
    outstanding_account_id = fields.Many2one('account.account', string='Cuenta pendiente')
    receivable_account_id = fields.Many2one('account.account', string='Cuenta intermediaria')
    company_id = fields.Many2one('res.company', string='Empresa')

    is_journal_bank = fields.Boolean("¿Es un diario bancario?", compute='_compute_is_journal_bank', store=True)

    @api.depends('journal_id')
    def _compute_payment_method_in_domain(self):
        for rec in self:
            if rec.journal_id.inbound_payment_method_line_ids:
                method_ids = rec.journal_id.inbound_payment_method_line_ids.ids
                domain = [('id', 'in', method_ids)]
            else:
                domain = []
            rec.payment_method_in_domain = json.dumps(domain)

    @api.depends('journal_id')
    def _compute_payment_method_out_domain(self):
        for rec in self:
            if rec.journal_id.outbound_payment_method_line_ids:
                method_ids = rec.journal_id.outbound_payment_method_line_ids.ids
                domain = [('id', 'in', method_ids)]
            else:
                domain = []
            rec.payment_method_out_domain = json.dumps(domain)

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id.type != 'bank':
            self.outstanding_account_id = False
        if self.journal_id.currency_id:
            self.currency_id = self.journal_id.currency_id
        else:
            self.currency_id = self.env.company.currency_id

    @api.depends('journal_id')
    def _compute_is_journal_bank(self):
        for record in self:
            record.is_journal_bank = record.journal_id.type == 'bank'


class CashManagementBill(models.Model):
    _name = "cash.management.bill"
    _description = "Monedas/Billetes"

    name = fields.Char("Name")
    value = fields.Float("Valor de la moneda", required=True, digits=(16, 4))
    is_for_all_config = fields.Boolean(
        "Para todas las cajas",
        default=True,
        help="Si está seleccionado, estas monedas y billetes estarán disponible en todas las Cajas"
    )
    config_ids = fields.Many2many("cash.management.config", string="Cajas")

    @api.onchange('is_for_all_config')
    def _onchange_is_for_all_config(self):
        if self.is_for_all_config:
            self.config_ids = [(5,)]

    @api.model
    def get_bills_for_config(self, config):
        """
        Retorna los billetes/monedas que aplican para la caja dada (config)
        """
        if not config:
            return self.env['cash.management.bill']

        domain = ['|', ('is_for_all_config', '=', True), ('config_ids', 'in', config.id)]
        return self.search(domain)


class CashManagementConfig(models.Model):
    _name = "cash.management.config"
    _description = "Caja"

    name = fields.Char("Nombre", required=True)
    parent_id = fields.Many2one('cash.management.config', string='Caja Padre', index=True, ondelete='restrict',
                                check_company=True)
    child_ids = fields.One2many('cash.management.config', 'parent_id', string='Cajas Hijas')
    is_cash_control = fields.Boolean("¿Controla billete y moneda?")
    payment_method_id = fields.Many2many(
        'cash.management.payment.method',
        string='Diarios de caja',
        required=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        required=True,
        help="Diario para registrar otras transacciones",
        domain="[('type', 'in', ['bank', 'cash'])]"
    )
    bank_transfer_journal_ids = fields.Many2many(
        'account.journal',
        string='Diarios para Transferencias a Banco',
        help="Seleccione los diarios utilizados para realizar transferencias desde esta caja.",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]"
    )
    cash_transfer_account_id = fields.Many2one('account.account', string='Cuenta transferencia entre cajas',
                                               domain=[('deprecated', '=', False)])
    currency_id = fields.Many2one('res.currency', string='Moneda')
    employee_ids = fields.Many2many('hr.employee', string='Usuarios')
    company_id = fields.Many2one('res.company', string='Empresa', required=True)
    payment_method_id_domain = fields.Char(compute='_compute_payment_method_id_domain')
    last_closing_date = fields.Datetime(
        string="Fecha de cierre", compute="_compute_last_closing_data", store=False
    )
    previous_balance = fields.Monetary(
        string="Saldo anterior", compute="_compute_last_closing_data", store=False, currency_field='currency_id'
    )
    previous_balance_doc_to_pay = fields.Monetary(
        string="Saldo anterior doc. pagar", compute="_compute_last_closing_data", store=False,
        currency_field='currency_id'
    )
    has_open_session = fields.Boolean(string="¿Tiene sesión abierta?", compute="_compute_has_open_session")
    pending_income_transfer_count = fields.Integer(
        string='Transferencias entrantes pendientes',
        compute='_compute_pending_income_transfer_count',
        store=False
    )
    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    cash_transfer_target_ids = fields.Many2many(
        'cash.management.config',
        'cash_management_config_transfer_rel',
        'source_config_id', 'target_config_id',
        string='Transferencias a Cajas',
        domain="[('id', '!=', id), ('company_id', '=', company_id), ('currency_id', '=', currency_id)]",
        help="Cajas de destino a las cuales se puede transferir efectivo desde esta caja."
    )

    @api.depends('name', 'company_id.name')
    def _compute_display_name(self):
        show_company = len(self.env.companies) > 1
        for rec in self:
            parts = [
                rec.name,
                f"({rec.company_id.name})" if show_company else ''
            ]
            rec.display_name = ' '.join(filter(None, parts))

    def _kanban_dashboard(self):
        dashboard_data = self._get_config_dashboard_data_batched()
        for config in self:
            config.kanban_dashboard = json.dumps(dashboard_data[config.id])

    def _compute_pending_income_transfer_count(self):
        CashFundTrasnfer = self.env['cash.fund.transfer']
        for config in self:
            config.pending_income_transfer_count = CashFundTrasnfer.search_count([
                ('destination_config_id', '=', config.id),
                ('type', '=', 'income'),
                ('session_id', '=', False),
            ])

    @api.depends_context('user_id')
    @api.depends('company_id')
    def _compute_has_open_session(self):
        CashManagementSession = self.env['cash.management.session']
        for record in self:
            record.has_open_session = CashManagementSession.search_count([
                ('company_id', '=', record.company_id.id),
                ('config_id', '=', record.id),
                ('state', '=', 'opened')
            ]) > 0

    @api.depends_context('user_id')
    @api.depends('company_id')
    def _compute_last_closing_data(self):
        CashManagementSession = self.env['cash.management.session']
        for record in self:
            session = CashManagementSession.sudo().search(
                [
                    ('config_id', '=', record.id),
                    ('company_id', '=', record.company_id.id),
                    ('state', 'in', ('closed', 'approved')),
                ],
                order='date_close desc',
                limit=1
            )
            record.last_closing_date = session.date_close
            record.previous_balance = session.balance_end_real or float(0)
            record.previous_balance_doc_to_pay = session.balance_end_r_doc_to_pay or float(0)

    @api.depends_context('user_id')
    @api.depends('company_id')
    def _compute_payment_method_id_domain(self):
        for rec in self:
            rec.payment_method_id_domain = ""
            company = rec.company_id
            if company:
                domain = ['|', ('company_id', '=', company.id), ('company_id', '=', False)]
            else:
                domain = [('company_id', '=', False)]
            rec.payment_method_id_domain = json.dumps(domain)

    def action_open_new_session(self):
        self.ensure_one()
        # 🔒 Validación: no permitir abrir si ya hay una sesión abierta
        open_session = self.env['cash.management.session'].sudo().search(
            [
                ('company_id', '=', self.company_id.id),
                ('config_id', '=', self.id),
                ('state', '=', 'opened'),
            ],
            limit=1
        )

        if open_session:
            raise ValidationError(_(
                "No se puede abrir una nueva sesión de caja.\n\n"
                "Ya existe una sesión abierta (%s) iniciada el %s por %s.\n\n"
                "Debe cerrar la sesión actual antes de abrir una nueva."
            ) % (
                                      open_session.name,
                                      format_datetime(self.env, open_session.date_open),
                                      open_session.user_id.name,
                                  ))

        # Obtener billetes que aplican a esta caja
        applicable_bills = self.env['cash.management.bill'].get_bills_for_config(self)

        bill_lines = [(0, 0, {
            'bill_id': bill.id,
            'quantity': 0,
        }) for bill in applicable_bills]

        opening_control = self.env['cash.management.opening.control.wizard'].sudo().create({
            'config_id': self.id,
            'currency_id': self.currency_id.id,
            'balance_start': self.previous_balance,
            'document_balance': self.previous_balance_doc_to_pay,
            'bill_ids': bill_lines,
        })
        opening_control_action = self.env.ref('cash_management_q.action_cash_management_opening_control_wizard').sudo()
        opening_control_action = opening_control_action.read()[0]
        opening_control_action['res_id'] = opening_control.id
        return opening_control_action

    def action_open_last_session(self):
        self.ensure_one()

        last_session = self.env['cash.management.session'].search(
            [('config_id', '=', self.id), ('company_id', '=', self.company_id.id), ('state', '=', 'opened')],
            order='create_date desc',
            limit=1
        )

        if not last_session:
            return True

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sesión de Caja',
            'res_model': 'cash.management.session',
            'res_id': last_session.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_pending_transfers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transferencias Entrantes Pendientes',
            'res_model': 'cash.fund.transfer',
            'view_mode': 'list',
            'domain': [
                ('destination_config_id', '=', self.id),
                ('type', '=', 'income'),
                ('session_id', '=', False)
            ],
            'target': 'current',
            'context': {'config_id': self.id, },
        }

    def _get_config_dashboard_data_batched(self):
        dashboard_data = {}
        for config in self:
            dashboard_data[config.id] = {
                'show_company': len(self.env.companies) > 1 or config.company_id.id != self.env.company.id,
            }
        return dashboard_data

    @api.model
    def _get_default_cash_config_domain(self):
        return [('employee_ids.user_id', '=', self.env.user.id)]

    @api.model
    def _search(self, args, offset=0, limit=None, order=None):
        """
        - Aplica el filtro por empleado (employee_ids.user_id = user.id)
        - EXCEPTO si:
            * es superusuario
            * o viene context {'bypass_cash_config_rule': True}
            * o el dominio ya filtra por id (id in ...)
        """
        args = args or []
        ctx = self.env.context or {}

        bypass = ctx.get('bypass_cash_config_rule', False)

        # Detectar si ya hay filtro por id (id in [...])
        has_id_in_filter = any(
            isinstance(arg, (tuple, list))
            and len(arg) >= 3
            and arg[0] == 'id'
            and arg[1] in ('in', '=', 'child_of')
            for arg in args
        )

        if (
                self._uid != SUPERUSER_ID
                and not self.env.user._is_admin()
                and not self.env.su
                and not bypass
                and not has_id_in_filter
        ):
            added_domain = self._get_default_cash_config_domain()
            args = expression.AND([
                expression.normalize_domain(args),
                added_domain
            ])

        return super(CashManagementConfig, self)._search(
            args, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby,
                   offset=0, limit=None, orderby=False, lazy=True):
        """
        Misma idea que en _search pero para las agregaciones (kanban, agrupados, etc).
        """
        domain = domain or []
        ctx = self.env.context or {}

        bypass = ctx.get('bypass_cash_config_rule', False)

        if self._uid != SUPERUSER_ID and not self.env.su and not self.env.user._is_admin() and not bypass:
            added_domain = self._get_default_cash_config_domain()
            domain = expression.AND([
                expression.normalize_domain(domain),
                added_domain
            ])

        return super(CashManagementConfig, self).read_group(
            domain, fields, groupby,
            offset=offset, limit=limit,
            orderby=orderby, lazy=lazy
        )
