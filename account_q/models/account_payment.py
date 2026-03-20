from odoo import fields, models, api, _
from odoo.exceptions import UserError, RedirectWarning
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    vat_refund_applicable = fields.Boolean(
        string="Aplica devolución de impuestos",
        compute='_compute_vat_refund_applicable',
        store=True
    )
    hide_account_receivable_id = fields.Boolean(
        compute="_compute_hide_account_fields",
        store=False,
    )
    hide_account_payable_id = fields.Boolean(
        compute="_compute_hide_account_fields",
        store=False,
    )
    account_receivable_id = fields.Many2one('account.account',
                                            string="Cuenta a cobrar",
                                            domain="[('account_type', 'in', ('asset_receivable',)), ('deprecated', '=', False), '|', ('currency_id', '=', currency_id), ('currency_id', '=', False)]")
    account_payable_id = fields.Many2one('account.account',
                                         string="Cuenta a pagar",
                                        domain="[('account_type', 'in', ('liability_payable', 'liability_credit_card')), '|', ('currency_id', '=', currency_id), ('currency_id', '=', False)]")

    @api.onchange('partner_id', 'currency_id')
    def _onchange_partner_currency_accounts(self):
        if self.partner_id and self.currency_id:
            partner_account = self.env['res.partner.account'].search([
                ('partner_id', '=', self.partner_id.id),
                ('currency_id', '=', self.currency_id.id),
                ('company_id', '=', self.company_id.id)
            ])

            if partner_account and self.partner_type == 'customer':
                self.account_receivable_id = partner_account.account_receivable_id.id
                self.account_payable_id = False
            elif partner_account and self.partner_type == 'supplier':
                self.account_receivable_id = False
                self.account_payable_id = partner_account.account_payable_id.id
            else:
                self.account_receivable_id = False
                self.account_payable_id = False

        if self.partner_id and self.currency_id:
            partner_bank = self.partner_id.bank_ids.filtered(lambda x: x.currency_id == self.currency_id)
            if partner_bank:
                partner_bank = partner_bank[0]
            self.partner_bank_id = partner_bank.id

    @api.depends('journal_id', 'partner_id', 'partner_type')
    def _compute_destination_account_id(self):
        super()._compute_destination_account_id()
        for pay in self:
            if pay.partner_type == 'customer':
                if pay.partner_id and pay.account_receivable_id and pay.payment_type == "inbound":
                    pay.destination_account_id = pay.account_receivable_id
                elif pay.partner_id and pay.account_payable_id and pay.payment_type == "outbound":
                    pay.destination_account_id = pay.account_payable_id
            elif pay.partner_type == 'supplier':
                if pay.partner_id and pay.account_payable_id and pay.payment_type == "outbound":
                    pay.destination_account_id = pay.account_payable_id
                elif pay.partner_id and pay.account_receivable_id and pay.payment_type == "inbound":
                    pay.destination_account_id = pay.account_receivable_id

    @api.depends("payment_type")
    def _compute_hide_account_fields(self):
        for payment in self:
            ctx_payment_type = payment.env.context.get("default_payment_type")
            payment.hide_account_receivable_id = False
            payment.hide_account_payable_id = False
            if ctx_payment_type == "outbound": # pago menu proveedor
                if payment.payment_type == "outbound":
                    payment.hide_account_receivable_id = True
                elif payment.payment_type == "inbound":
                    payment.hide_account_payable_id = True
                    payment.hide_account_receivable_id = False
            elif ctx_payment_type == "inbound": # pago menu cliente
                if payment.payment_type == "outbound":
                    payment.hide_account_payable_id = False
                    payment.hide_account_receivable_id = True
                elif payment.payment_type == "inbound":
                    payment.hide_account_payable_id = True

    @api.depends('payment_method_line_id')
    def _compute_vat_refund_applicable(self):
        """
        Calcula si el pago aplica devolución de IVA, siguiendo la lógica de account.payment.register.
        """
        for rec in self:
            applicable = False
            method_line = rec.payment_method_line_id
            if method_line and method_line.apply_vat_refund:
                invoices, doc_types_configured, applies = rec._get_invoice_vat_refund_flags()
                if applies == {True}:
                    applicable = True
            rec.vat_refund_applicable = applicable

    def _get_invoice_vat_refund_flags(self):
        """
        Retorna una tupla: (invoices, doc_types_configured, applies_set)
        - invoices: recordset de account.move
        - doc_types_configured: lista de ids de l10n_latam.document.type
        - applies_set: set con valores booleanos {True, False} indicando si aplica devolución por cada factura
        """
        # Determinar las facturas relacionadas al pago
        invoices = self.invoice_ids

        # Buscar todos los document_type_id configurados en tax.refund.legislation.config
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

    def _sync_destination_account_to_move(self):
        """
        Si el pago ya tiene asiento en borrador (revertido a draft),
        actualiza la cuenta del apunte de contrapartida según el destino actual.
        """
        for payment in self:
            move = payment.move_id
            destination = None
            if payment.payment_type == 'outbound':
                destination = payment.account_payable_id
                account_types = ('liability_payable',)
            else:
                destination = payment.account_receivable_id
                account_types = ('asset_receivable',)
                if payment.partner_type == 'supplier':
                    account_types = ('asset_receivable', 'liability_payable')

            if not move or move.state not in ('posted', 'draft') or not destination:
                continue
            lines = move.line_ids.filtered(
                lambda l: l.partner_id == payment.partner_id
                and l.account_id.account_type in account_types
            )
            lines_to_update = lines.filtered(lambda l: l.account_id != destination)
            if lines_to_update:
                lines_to_update.write({'account_id': destination.id})

    def action_post(self):
        # sincronizar el asiento antes de postear.
        res = super().action_post()
        self._sync_destination_account_to_move()
        return res



class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    _PAYMENT_QUEUE_ACTIVE_STATES = ('failed', 'pending', 'enqueued', 'started', 'wait_dependencies')

    payment_queue_count = fields.Integer(string='Cantidad de pagos en cola',
                                         help='Cantidad total de pagos que se van a generar')
    processing_queue = fields.Boolean(string='Cola de procesamiento pagos', default=False)
    payment_generated_count = fields.Integer(string='Pagos generados', compute='_compute_payment_generated_count')

    @api.depends('payment_ids')
    def _compute_payment_generated_count(self):
        for batch in self:
            batch.payment_generated_count = len(batch.payment_ids)

    def rollback_batch_payments(self):
        """
        Revierte todos los pagos del lote:
        - Pasa a borrador si no lo están
        - Luego los elimina
        """
        for batch in self:
            payments = batch.payment_ids
            for payment in payments.filtered(lambda p: p.state != 'draft'):
                payment.action_draft()
            count = len(payments)
            payments.unlink()
            _logger.info('Lote ID %s revertido: %s pagos eliminados', batch.id, count)

    def _get_active_payment_queue_jobs(self):
        self.ensure_one()
        jobs = self.env['queue.job'].search([
            ('model_name', '=', 'automatic.debit.payment.wizard'),
            ('method_name', '=', '_job_generate_payments'),
            ('state', 'in', self._PAYMENT_QUEUE_ACTIVE_STATES),
        ])
        return jobs.filtered(
            lambda job: len(job.args) > 1 and job.args[1] == self.id
        )

    def _has_active_payment_queue_jobs(self):
        self.ensure_one()
        return bool(self._get_active_payment_queue_jobs())

    def _needs_check_warning(self):
        self.ensure_one()
        if not self.processing_queue and not self._has_active_payment_queue_jobs():
            return False
        return (
            self.payment_queue_count > len(self.payment_ids)
            and self._has_active_payment_queue_jobs()
        )

    def action_check_with_warning(self):
        self.ensure_one()
        if self._needs_check_warning():
            return {
                'type': 'ir.actions.act_window',
                'name': _('Confirmar comprobacion'),
                'res_model': 'account.batch.payment.check.confirmation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_batch_id': self.id,
                },
            }
        self.with_context(force_check=True).write({'is_checked': True})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def write(self, vals):
        for batch in self:
            if 'is_checked' in vals and vals['is_checked'] is True:
                if batch.processing_queue and batch._needs_check_warning() and not self.env.context.get('force_check'):
                    action = self.env.ref(
                        'account_q.action_batch_payment_check_confirmation_wizard'
                    ).read()[0]
                    action['context'] = {'default_batch_id': batch.id}
                    raise RedirectWarning(
                        _(
                            "No se debe marcar como comprobado.\n"
                            "Cantidad esperada: %(expected)s\n"
                            "Cantidad actual: %(current)s\n\n"
                            "Aun no se han generado todos los pagos del lote."
                        ) % {
                            'expected': batch.payment_queue_count,
                            'current': len(batch.payment_ids),
                        },
                        action,
                        _('Continuar')
                    )
        return super(AccountBatchPayment, self).write(vals)
