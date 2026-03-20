# -*- coding: utf-8 -*-
import json
from collections import defaultdict
from odoo.tools import frozendict

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MultiInvoicePaymentWizard(models.TransientModel):
    _name = 'multi.invoice.payment.wizard'
    _description = 'Wizard para Pagos Múltiples de Facturas'

    payment_date = fields.Date(
        string='Fecha de Pago',
        required=True,
        default=fields.Date.context_today
    )
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas a Pagar',
        required=True,
        domain="[('state', '=', 'posted'), ('payment_state', 'in', ('not_paid', 'partial')), ('move_type', 'in', ('in_invoice', 'out_invoice'))]"
    )
    payment_line_ids = fields.One2many(
        'multi.invoice.payment.line',
        'wizard_id',
        string='Líneas de Pago',
        required=True
    )
    move_type = fields.Selection(
        [('in_invoice', 'Entrada'), ('out_invoice', 'Salida'), ('out_receipt', 'Recibos')],
        string='Tipo de Movimiento',
        required=True,
        default='out_invoice'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company
    )
    invoice_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de las Facturas',
    )
    total_amount_to_pay = fields.Monetary(
        string='Total por pagar',
        compute='_compute_total_amount_to_pay',
        currency_field='invoice_currency_id',
        store=True,
        help="Suma total de los saldos pendientes de las facturas seleccionadas"
    )
    total_amount_paid = fields.Monetary(
        string='Total a pagar',
        compute='_compute_total_amount_paid',
        currency_field='invoice_currency_id',
        store=True,
        help="Suma total de los pagos realizados"
    )
    total_amount_residual = fields.Monetary(
        string='Total pendiente de pagar',
        compute='_compute_total_amount_paid',
        currency_field='invoice_currency_id',
        store=True,
        help="Suma total de los pagos realizados"
    )
    log = fields.Char(string='Log')

    show_payment_difference = fields.Boolean(compute='_compute_total_amount_paid')
    payment_difference_handling = fields.Selection(
        string="Diferencia de pago",
        selection=[('open', 'Mantener abierto'), ('reconcile', 'Marcar como pagado en su totalidad')],
        default='open',
        store=True,
        readonly=False,
    )
    writeoff_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Publicar la diferencia en",
        copy=False,
        domain="[('deprecated', '=', False)]",
        check_company=True,
    )
    writeoff_label = fields.Char(string='Etiqueta', default='Write-Off',
                                 help='Change label of the counterpart that will hold the payment difference')

    is_payments_generated = fields.Boolean(string='¿Se han generado los pagos?', default=False)
    additional_info = fields.Text('Datos adicionales')
    memo = fields.Char(string='Memo', compute='_compute_memo', store=True, readonly=False)

    @api.depends('invoice_ids', 'invoice_ids.payment_reference', 'invoice_ids.ref', 'invoice_ids.name')
    def _compute_memo(self):
        valid_account_types = self.env['account.payment']._get_valid_payment_account_types()
        for wizard in self:
            lines = wizard._get_memo_lines(valid_account_types)
            wizard.memo = self._get_communication(lines) if lines else False

    def _get_memo_lines(self, valid_account_types):
        self.ensure_one()
        available_lines = self.env['account.move.line']
        for line in self.invoice_ids.line_ids:
            if line.account_type not in valid_account_types:
                continue
            if line.currency_id:
                if line.currency_id.is_zero(line.amount_residual_currency):
                    continue
            else:
                if line.company_currency_id.is_zero(line.amount_residual):
                    continue
            available_lines |= line
        return available_lines

    def _get_communication(self, lines):
        if len(lines.move_id) == 1:
            move = lines.move_id
            label = move.payment_reference or move.ref or move.name
        elif any(move.is_outbound() for move in lines.move_id):
            labels = {move.payment_reference or move.ref or move.name for move in lines.move_id}
            return ', '.join(sorted(filter(lambda l: l, labels)))
        else:
            label = self.company_id.get_next_batch_payment_communication()
        return label

    @api.depends('payment_date', 'move_type', 'company_id')
    def _compute_display_name(self):
        for wizard in self:
            move_type_label = dict(self._fields['move_type'].selection).get(wizard.move_type, '')
            date_str = wizard.payment_date.strftime('%d/%m/%Y') if wizard.payment_date else ''
            wizard.display_name = '%s - %s' % (move_type_label, date_str)

    @api.depends('invoice_ids.amount_residual', 'invoice_currency_id')
    def _compute_total_amount_to_pay(self):
        """Calcula el total a pagar sumando los saldos pendientes de las facturas"""
        for record in self:
            _total_amount_to_pay = sum(inv.amount_residual for inv in record.invoice_ids)
            record.total_amount_to_pay = _total_amount_to_pay

    @api.depends('payment_line_ids.amount')
    def _compute_total_amount_paid(self):
        """Calcula el total pagado sumando los montos de las líneas de pago"""
        for record in self:
            record.total_amount_paid = sum(line.amount_currency for line in record.payment_line_ids)
            record.total_amount_residual = record.total_amount_to_pay - record.total_amount_paid
            record.show_payment_difference = record.total_amount_residual != float(0)

    @api.constrains('payment_line_ids')
    def _check_payment_lines(self):
        """Validar que haya al menos una línea de pago"""
        if not self.payment_line_ids:
            raise ValidationError(_('Debe agregar al menos una línea de pago.'))

    def _get_invoice_vat_refund_flags(self):
        """
        Retorna una tupla: (invoices, doc_types_configured, applies_set)
        - invoices: recordset de account.move
        - doc_types_configured: lista de ids de l10n_latam.document.type
        - applies_set: set con valores booleanos {True, False} indicando si aplica devolución por cada factura
        """
        invoices = self.invoice_ids

        # Buscar todos los document_type_id configurados en tax.refund.legislation.config
        # Buscar todos los document_type_id y sus tax_id configurados en tax.refund.legislation.config
        config_records = self.env['tax.refund.legislation.config'].search([
            ('document_type_id', '!=', False),
            ('tax_ids', '!=', False)
        ])
        # Construir un set de tuplas (document_type_id, tax_id) válidas
        doc_type_tax_pairs = set()
        for rec in config_records:
            for tax in rec.tax_ids:
                doc_type_tax_pairs.add((rec.document_type_id.id, tax.id))

        doc_types_configured = list({rec.document_type_id.id for rec in config_records})

        # Para cada factura, verificar si existe al menos una línea con un tax_id tal que
        # (document_type_id, tax_id) esté en la configuración
        applies_set = set(
            any(
                (inv.l10n_latam_document_type_id.id, tax_id) in doc_type_tax_pairs
                for line in inv.invoice_line_ids
                for tax_id in line.tax_ids.ids
            )
            for inv in invoices
        )
        return invoices, doc_types_configured, applies_set

    def action_generate_payments_vat_refund_check(self):
        self.ensure_one()
        self._check_is_valid()
        if not self.env.context.get('force_skip_vat_refund_check') and self.payment_line_ids.filtered(
                lambda l: l.payment_method_line_id.payment_method_id.code == 'pos'):
            invoices, doc_types_configured, applies = self._get_invoice_vat_refund_flags()
            if applies == {True, False}:
                n_context = dict(self.env.context)
                n_context['multi_invoice_payment_id'] = self.id
                return {
                    'name': 'Advertencia de devolución de IVA',
                    'type': 'ir.actions.act_window',
                    'res_model': 'vat.refund.confirmation.multi.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': n_context,
                }
        return self.action_generate_payments()

    def action_generate_payments(self):
        """Generar los pagos distribuyendo automáticamente entre las facturas"""
        self.ensure_one()
        self._check_is_valid()

        payments_grouped_dict = {}

        # Ordenar facturas por fecha y número (orden de pago)
        sorted_invoices = self.invoice_ids.sorted(lambda inv: (inv.invoice_date, inv.name))

        created_payments = self.env['account.payment']
        consolidated_ref = self.env['ir.sequence'].with_context(company_id=self.company_id.id).next_by_code(
            'account.payment.consolidated')
        # Procesar cada línea de pago
        for payment_line in self.payment_line_ids:
            created_payments_line = self.env['account.payment']
            remaining_amount = payment_line.amount

            # Buscar facturas que aún necesitan pago
            unpaid_invoices = sorted_invoices.filtered(lambda inv: inv.amount_residual > 0)

            while remaining_amount > 0 and unpaid_invoices:
                # Tomar la primera factura no pagada y agrupar por el mismo partner
                first_invoice = unpaid_invoices[0]
                partner = first_invoice.partner_id
                partner_invoices = unpaid_invoices.filtered(lambda inv: inv.partner_id == partner)

                # Seleccionar tantas facturas del partner como alcance el monto restante
                selected_invoices = self.env['account.move']
                accumulated_amount_in_line_currency = 0.0
                for invoice in partner_invoices:
                    if accumulated_amount_in_line_currency >= remaining_amount:
                        break
                    # Convertir el saldo de la factura a la moneda de la línea de pago
                    invoice_residual_in_line_currency = payment_line.invoice_currency_id._convert(
                        invoice.amount_residual,
                        payment_line.currency_id,
                        date=self.payment_date,
                        round=False
                    )
                    if payment_line.currency_id.is_zero(invoice_residual_in_line_currency):
                        continue
                    selected_invoices |= invoice
                    accumulated_amount_in_line_currency += invoice_residual_in_line_currency

                if not selected_invoices:
                    break

                # Monto a registrar en la moneda de la línea (puede ser parcial sobre la última factura)
                amount_to_register_line_currency = min(remaining_amount, accumulated_amount_in_line_currency)

                # Preparar el wizard de pagos agrupados
                vals = payment_line._prepare_payment_line_values(amount_to_register_line_currency)
                vals.update({
                    'additional_info': self.additional_info,
                    'communication': self.memo,
                })

                register_wizard = self.env['account.payment.register'].with_context(
                    consolidated_sequence_ref=consolidated_ref,
                    active_model='account.move',
                    active_ids=selected_invoices.ids,
                    skip_pos_request=True,
                    default_invoice_ids=[(6, 0, selected_invoices.ids)],
                ).create(vals)
                register_wizard.communication = self.memo

                try:
                    # Crear pagos y reconciliar; devuelve los payments creados
                    # Verificar si se está usando el remaining_amount completo
                    is_using_full_remaining = accumulated_amount_in_line_currency > remaining_amount
                    is_last_payment_line = self.payment_line_ids[-1].id == payment_line.id

                    if register_wizard.show_payment_difference and (is_last_payment_line and is_using_full_remaining):
                        register_wizard.with_context(
                            consolidated_sequence_ref=consolidated_ref,
                            active_model='account.move',
                            active_ids=selected_invoices.ids,
                            default_invoice_ids=[(6, 0, selected_invoices.ids)],
                        ).write({
                            'payment_difference_handling': self.payment_difference_handling,
                            'writeoff_account_id': self.writeoff_account_id,
                            'writeoff_label': self.writeoff_label,
                        })
                    payments = register_wizard._create_payments()
                    payments.write({
                        'check_number': payment_line.check_number,
                        'check_due_date': payment_line.check_due_date,
                    })
                    payments_grouped_dict[str(payments.ids)] = selected_invoices.ids
                    created_payments |= payments
                    created_payments_line |= payments

                    # Actualizar el monto restante
                    remaining_amount -= amount_to_register_line_currency

                    # Recalcular facturas impagas
                    unpaid_invoices = sorted_invoices.filtered(lambda inv: inv.amount_residual > 0)

                except Exception as e:
                    raise UserError(_('Error al procesar el pago: %s') % str(e))

            # Asignar pagos generados a la línea del wizard
            payment_line.payment_ids = [(6, 0, created_payments_line.ids)]

        if not created_payments:
            raise UserError(_('No se pudieron generar los pagos.'))

        for payment_ids, invoice_ids in payments_grouped_dict.items():
            payments = created_payments.browse(json.loads(payment_ids))
            payments.invoice_ids = [(6, 0, invoice_ids)]

        # Obtener el action base según el tipo de movimiento
        if self.move_type in ('out_invoice', 'out_receipt'):
            base_action = self.env.ref('account.action_account_payments')
            view_id = self.env.ref('account.view_account_payment_tree')
        else:
            base_action = self.env.ref('account.action_account_payments_payable')
            view_id = self.env.ref('account.view_account_supplier_payment_tree')

        # Crear un nuevo action basado en el action existente

        self.is_payments_generated = True
        action = base_action.read()[0]
        action.update({
            'name': _('Pagos Generados'),
            'domain': [('id', 'in', created_payments.ids)],
            'view_mode': 'list,form',
            'view_id': view_id.id,
            'target': 'current',
        })

        return action

    def _check_is_valid(self):
        """Validar que los datos sean válidos"""
        if not self.invoice_ids:
            raise UserError(_('No hay facturas seleccionadas para procesar.'))
        if not self.payment_line_ids:
            raise UserError(_('No hay líneas de pago configuradas.'))

        for line in self.payment_line_ids:
            if not line.payment_method_line_id:
                raise UserError(_('Debe seleccionar un método de pago para todas las líneas.'))
            if line.amount <= 0:
                raise UserError(_('El monto debe ser mayor a 0 en todas las líneas de pago.'))

        if not self.payment_date:
            raise UserError(_('Debe seleccionar una fecha de pago.'))

    def _get_batches(self):
        lines = self.mapped('invoice_ids').mapped('line_ids')._origin

        batches = defaultdict(lambda: {'lines': self.env['account.move.line']})
        banks_per_partner = defaultdict(lambda: {'inbound': set(), 'outbound': set()})
        for line in lines:
            batch_key = self._get_line_batch_key(line)
            vals = batches[frozendict(batch_key)]
            vals['payment_values'] = batch_key
            vals['lines'] += line
            banks_per_partner[batch_key['partner_id']]['inbound' if line.balance > 0.0 else 'outbound'].add(
                batch_key['partner_bank_id']
            )

        partner_unique_inbound = {p for p, b in banks_per_partner.items() if len(b['inbound']) == 1}
        partner_unique_outbound = {p for p, b in banks_per_partner.items() if len(b['outbound']) == 1}

        # Compute 'payment_type'.
        batch_vals = []
        seen_keys = set()
        for i, key in enumerate(list(batches)):
            if key in seen_keys:
                continue
            vals = batches[key]
            lines = vals['lines']
            merge = (
                    batch_key['partner_id'] in partner_unique_inbound
                    and batch_key['partner_id'] in partner_unique_outbound
            )
            if merge:
                for other_key in list(batches)[i + 1:]:
                    if other_key in seen_keys:
                        continue
                    other_vals = batches[other_key]
                    if all(
                            other_vals['payment_values'][k] == v
                            for k, v in vals['payment_values'].items()
                            if k not in ('partner_bank_id', 'payment_type')
                    ):
                        # add the lines in this batch and mark as seen
                        lines += other_vals['lines']
                        seen_keys.add(other_key)
            balance = sum(lines.mapped('balance'))
            vals['payment_values']['payment_type'] = 'inbound' if balance > 0.0 else 'outbound'
            if merge:
                partner_banks = banks_per_partner[batch_key['partner_id']]
                vals['partner_bank_id'] = partner_banks[vals['payment_values']['payment_type']]
                vals['lines'] = lines
            batch_vals.append(vals)
        return batch_vals


class MultiInvoicePaymentLine(models.TransientModel):
    _name = 'multi.invoice.payment.line'
    _description = 'Línea de Pago'

    wizard_id = fields.Many2one(
        'multi.invoice.payment.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    invoice_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de las Facturas',
        related='wizard_id.invoice_currency_id',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        required=True,
    )
    journal_id_domain = fields.Char(
        compute='_compute_journal_id_domain',
        store=False
    )
    move_type = fields.Selection(
        string='Tipo de Movimiento',
        required=True,
        related='wizard_id.move_type',
    )
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Método de Pago',
        required=True,
    )
    available_payment_method_line_ids = fields.Many2many(
        comodel_name="account.payment.method.line",
        compute="_compute_available_payment_method_line_ids",
    )
    is_check = fields.Boolean(
        string='Es Cheque',
        related='payment_method_line_id.is_check',
        help="Si es cheque, se mostrará el número de chequera y la fecha de vencimiento."
    )
    payment_type = fields.Selection(
        [('inbound', 'Entrada'), ('outbound', 'Salida')],
        string='Tipo de Pago',
        compute='_compute_payment_type',
        store=True
    )
    amount = fields.Monetary(
        string='Monto a Pagar',
        currency_field='currency_id',
    )
    amount_currency = fields.Monetary(
        string='Monto a Pagar en Moneda',
        compute='_compute_amount_currency',
        store=True,
        currency_field='invoice_currency_id',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        related='wizard_id.company_id',
    )
    check_number = fields.Char(
        string='Número de Cheque',
        help="Número de chequera para pagos en cheque."
    )
    check_due_date = fields.Date(
        string='Fecha de Vencimiento',
        help="Fecha de vencimiento del cheque."
    )

    payment_ids = fields.Many2many(
        'account.payment',
        string='Pagos Generados',
        readonly=True,
        copy=False,
    )

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        """Actualizar el método de pago cuando cambia la moneda"""
        self.journal_id = False
        total_amount_residual = self._context.get('total_amount_residual', self.wizard_id.total_amount_residual)
        if self.currency_id:
            self.amount = self.invoice_currency_id._convert(
                total_amount_residual,
                self.currency_id,
                date=self.wizard_id.payment_date or fields.Date.today()
            )
        else:
            self.amount = 0

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Actualizar métodos de pago disponibles cuando cambia el diario"""
        self.payment_method_line_id = False

    @api.onchange('payment_method_line_id')
    def _onchange_payment_method_line_id(self):
        """Actualizar si es cheque cuando cambia el método de pago"""
        if not self.payment_method_line_id.is_check:
            self.check_number = False
            self.check_due_date = False

    @api.constrains('amount')
    def _check_amount(self):
        """Validar que el monto sea positivo"""
        for line in self:
            if line.amount <= 0:
                raise ValidationError(
                    _('El monto a pagar debe ser mayor a 0.')
                )

    @api.depends('move_type')
    def _compute_payment_type(self):
        """Determinar el tipo de pago basado en el tipo de facturas seleccionadas"""
        for line in self:
            if line.move_type == 'in_invoice':
                line.payment_type = 'inbound'
            else:
                line.payment_type = 'outbound'

    @api.depends('move_type', 'company_id', 'currency_id')
    def _compute_journal_id_domain(self):
        Journal = self.env['account.journal']
        for rec in self:
            is_company_currency = rec.currency_id == rec.company_id.currency_id
            if is_company_currency:
                journals = Journal.search([
                    *self.env['account.journal']._check_company_domain(rec.company_id),
                    ('type', 'in', ('bank', 'cash', 'credit')),
                    '|',
                    ('currency_id', '=', False),
                    ('currency_id', '=', rec.currency_id.id),
                ])
            else:
                journals = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(rec.company_id),
                    ('type', 'in', ('bank', 'cash', 'credit')),
                    ('currency_id', '=', rec.currency_id.id),
                ])
            if rec.move_type == 'in_invoice':
                journals = journals.filtered(lambda x: x.inbound_payment_method_line_ids)
            else:
                journals = journals.filtered(lambda x: x.outbound_payment_method_line_ids)
            domain = [('id', 'in', journals.ids)]
            rec.journal_id_domain = json.dumps(domain)

    @api.depends("journal_id")
    def _compute_available_payment_method_line_ids(self):
        for wizard in self:
            if wizard.journal_id:
                wizard.available_payment_method_line_ids = (
                    wizard.journal_id._get_available_payment_method_lines("inbound")
                )
            else:
                wizard.available_payment_method_line_ids = False

    @api.depends('wizard_id.payment_date', 'invoice_currency_id', 'currency_id', 'amount')
    def _compute_amount_currency(self):
        wizard = self.mapped('wizard_id')
        invoice_currency = wizard.invoice_currency_id or self.env.company.currency_id
        for line in self:
            is_multi_currency = invoice_currency != line.currency_id
            if not is_multi_currency:
                line.amount_currency = line.amount
            elif line.amount > 0:
                line.amount_currency = line.currency_id._convert(
                    line.amount,
                    line.invoice_currency_id,
                    date=wizard.payment_date
                )
            else:
                line.amount_currency = 0

    def button_residual_inline_currency(self):
        self.ensure_one()
        total_amount_residual = self.wizard_id.total_amount_residual
        self.amount = self.currency_id._convert(
            total_amount_residual,
            self.invoice_currency_id,
            date=self.wizard_id.payment_date
        )

    def _prepare_payment_line_values(self, amount_to_register_line_currency):
        self.ensure_one()
        vals = {
            'journal_id': self.journal_id.id,
            'payment_date': self.wizard_id.payment_date,
            'payment_method_line_id': self.payment_method_line_id.id,
            'amount': amount_to_register_line_currency,
            'currency_id': self.currency_id.id,
            'group_payment': True,
        }
        if self.is_check:
            vals['check_number'] = self.check_number
            vals['check_due_date'] = self.check_due_date
        return vals
