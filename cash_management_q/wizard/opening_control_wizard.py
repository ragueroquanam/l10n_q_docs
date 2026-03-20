# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError


class CashManagementOpeningControlWizard(models.TransientModel):
    _name = 'cash.management.opening.control.wizard'
    _description = 'Control de apertura'

    session_id = fields.Many2one('cash.management.session', string='Sesión')
    config_id = fields.Many2one('cash.management.config', string='Caja')
    is_cash_control = fields.Boolean("¿Controla billete y moneda?", related='config_id.is_cash_control')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    balance_start = fields.Monetary(string="Saldo de apertura", readonly=True)
    document_balance = fields.Monetary(string='Saldo doc. a pagar', store=True, readonly=True)
    bill_ids = fields.One2many(
        'cash.management.opening.control.wizard.line',
        'opening_control_id',
        string='Monedas/Billetes')
    opening_note = fields.Text(string="Nota de apertura")
    total_amount = fields.Monetary(
        string="Total Monedas/Billetes",
        compute='_compute_total_amount',
        currency_field='currency_id')

    @api.onchange('bill_ids')
    def _onchange_bill_ids_update_opening_note(self):
        lines = []
        total = 0.0
        currency = self.currency_id or self.env.company.currency_id

        for line in self.bill_ids:
            if line.quantity > 0:
                amount = line.quantity * line.value
                total += amount
                # Formatea en formato "3 x 0,20 $"
                formatted_value = f"{line.value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                lines.append(f"\t{int(line.quantity)} x {formatted_value} {currency.symbol}")

        if lines:
            formatted_total = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.opening_note = "Detalles de apertura:\n" + "\n".join(
                lines) + f"\nTotal: {formatted_total} {currency.symbol}"
        else:
            self.opening_note = False

    @api.depends('bill_ids.quantity', 'bill_ids.value')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(line.quantity * line.value for line in wizard.bill_ids)

    def button_confirm(self):
        self.ensure_one()
        if self.is_cash_control and tools.float_compare(self.balance_start, self.total_amount, precision_digits=2):
            raise ValidationError(_("El saldo de apertura no coincide con el total de monedas/billetes."))

        bill_lines = [(0, 0, {
            'bill_id': bill.bill_id.id,
            'quantity': bill.quantity,
        }) for bill in self.bill_ids]

        self.env['cash.management.session'].sudo().create({
            'company_id': self.config_id.company_id.id,
            'config_id': self.config_id.id,
            'user_id': self.env.user.id,
            'date_open': fields.Datetime.now(),
            'currency_id': self.currency_id.id,
            'opening_notes': self.opening_note,
            'balance_start': self.balance_start,
            'balance_start_doc_to_pay': self.document_balance,
            'bill_ids': bill_lines,
        })

    def action_open_cash_breakdown(self):
        self.ensure_one()

        # Crear el wizard con los valores por defecto
        breakdown_wizard = self.env['cash.management.opening.breakdown.wizard'].create({
            'origin_wizard_id': self.id,
            'currency_id': self.currency_id.id,
            'balance_start': self.balance_start,
        })

        # Crear las líneas del desglose basadas en bill_ids actuales
        CashManagementOpeningBreakdownLine = self.env['cash.management.opening.breakdown.line']
        for line in self.bill_ids:
            CashManagementOpeningBreakdownLine.create({
                'breakdown_wizard_id': breakdown_wizard.id,
                'bill_id': line.bill_id.id,
                'quantity': line.quantity,
            })

        # Retornar acción para abrir el wizard creado
        return {
            'type': 'ir.actions.act_window',
            'name': 'Desglose de Billetes y Monedas',
            'res_model': 'cash.management.opening.breakdown.wizard',
            'view_mode': 'form',
            'res_id': breakdown_wizard.id,
            'target': 'new',
        }


class CashManagementOpeningControlWizardLine(models.TransientModel):
    _name = 'cash.management.opening.control.wizard.line'
    _description = 'Control de apertura - Línea'

    opening_control_id = fields.Many2one(
        'cash.management.opening.control.wizard',
        string='Control de apertura',
        ondelete='cascade',
        required=True)
    session_id = fields.Many2one('cash.management.session', string='Sesión')
    config_id = fields.Many2one('cash.management.config', string='Caja', related='session_id.config_id', store=True)
    bill_id = fields.Many2one(
        'cash.management.bill',
        string='Moneda/Billete',
        domain="['|',('is_for_all_config', '=', True), ('config_ids', '=', config_id)]",
        required=True)
    value = fields.Float("Valor de la moneda", related='bill_id.value', digits=(16, 4))
    quantity = fields.Float("Cantidad", required=True)


class CashManagementOpeningBreakdownWizard(models.TransientModel):
    _name = 'cash.management.opening.breakdown.wizard'
    _description = 'Desglose de Billetes y Monedas'

    origin_wizard_id = fields.Many2one(
        'cash.management.opening.control.wizard',
        string='Wizard de apertura',
        required=True,
        ondelete='cascade'
    )
    currency_id = fields.Many2one('res.currency', string='Moneda')
    breakdown_line_ids = fields.One2many(
        'cash.management.opening.breakdown.line',
        'breakdown_wizard_id',
        string='Detalle de monedas y billetes'
    )
    balance_start = fields.Monetary(string="Saldo de apertura", readonly=True)
    total = fields.Monetary(string="Total Monedas/Billetes", compute="_compute_total", currency_field='currency_id')

    @api.depends('breakdown_line_ids.quantity', 'breakdown_line_ids.value')
    def _compute_total(self):
        for rec in self:
            rec.total = sum(line.quantity * line.value for line in rec.breakdown_line_ids)

    def action_confirm_breakdown(self):
        self.ensure_one()
        # Borrar líneas previas en el wizard padre
        self.origin_wizard_id.bill_ids.unlink()

        # Copiar desglose
        for line in self.breakdown_line_ids:
            self.origin_wizard_id.bill_ids.create({
                'opening_control_id': self.origin_wizard_id.id,
                'session_id': self.origin_wizard_id.session_id.id,
                'bill_id': line.bill_id.id,
                'quantity': line.quantity,
            })

        # Actualizar nota y balance desde el wizard padre
        self.origin_wizard_id._onchange_bill_ids_update_opening_note()
        self.origin_wizard_id.total_amount = self.total

        opening_control_action = self.env.ref('cash_management_q.action_cash_management_opening_control_wizard')
        opening_control_action = opening_control_action.read()[0]
        opening_control_action['res_id'] = self.origin_wizard_id.id
        return opening_control_action


class CashManagementOpeningBreakdownLine(models.TransientModel):
    _name = 'cash.management.opening.breakdown.line'
    _description = 'Línea de desglose temporal'

    breakdown_wizard_id = fields.Many2one(
        'cash.management.opening.breakdown.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    bill_id = fields.Many2one(
        'cash.management.bill',
        string='Billete / Moneda',
        required=True
    )
    value = fields.Float(string='Valor', related='bill_id.value', readonly=True)
    quantity = fields.Float(string='Cantidad', default=0.0)
