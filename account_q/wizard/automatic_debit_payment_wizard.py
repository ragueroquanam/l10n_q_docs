from odoo import models, fields, _, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AutomaticDebitPaymentWizard(models.TransientModel):
    _name = 'automatic.debit.payment.wizard'
    _description = 'Pagos por Débito Automático Wizard'

    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        required=True,
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]"
    )
    payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        string='Medios de Pago',
        domain="[('payment_type', '=', 'inbound')]",
        required=True
    )
    payment_date = fields.Date(string='Fecha de Pago', required=True, default=fields.Date.context_today)

    invoice_count = fields.Integer(
        string='Cantidad de Facturas',
        compute='_compute_invoice_count',
        store=False
    )

    @api.depends('payment_method_line_ids', 'journal_id', 'payment_date')
    def _compute_invoice_count(self):
        for wizard in self:
            if wizard.payment_method_line_ids:
                wizard.invoice_count = self.env['account.move'].search_count(
                    domain=wizard.domain_generate_payments()
                )
            else:
                wizard.invoice_count = 0

    @api.constrains('payment_method_line_ids')
    def _check_payment_method_line_types(self):
        for wizard in self:
            if wizard.payment_method_line_ids:
                types = wizard.payment_method_line_ids.mapped('payment_method_id.id')
                if len(set(types)) > 1:
                    raise UserError(_('Todos los métodos de pago seleccionados deben ser del mismo tipo.'))

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        self.payment_method_line_ids = False

    @api.onchange("payment_method_line_ids")
    def _onchange_journal_id(self):
        self._check_payment_method_line_types()

    def domain_generate_payments(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('payment_state', '=', 'not_paid'),
            ('preferred_payment_method_line_id', 'in', self.payment_method_line_ids.ids),
            ('company_id', '=', self.env.company.id),
        ]
        return domain

    def action_generate_payments(self):
        self.ensure_one()

        AccountMove = self.env['account.move']
        PaymentRegister = self.env['account.payment.register']
        BatchPayment = self.env['account.batch.payment']

        invoices_count = AccountMove.search_count(domain=self.domain_generate_payments())

        if not invoices_count:
            raise UserError(_('No se encontraron Facturas.'))

        BATCH_SIZE = 1000
        payments_ids = []
        for method_line in self.payment_method_line_ids:
            invoices = AccountMove.search_read(
                domain=[
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice'),
                    ('payment_state', '=', 'not_paid'),
                    ('preferred_payment_method_line_id', '=', method_line.id),
                    ('company_id', '=', self.env.company.id),
                ],
                fields=['id']
            )

            if not invoices:
                continue
            invoice_ids = [o['id'] for o in invoices]
            for i in range(0, len(invoice_ids), BATCH_SIZE):
                batch_ids = invoice_ids[i:i + BATCH_SIZE]
                register_payment_wizard = PaymentRegister.with_context(
                    active_model='account.move',
                    active_ids=batch_ids
                ).create({
                    'journal_id': self.journal_id.id,
                    'payment_date': self.payment_date,
                    'payment_method_line_id': method_line.id,
                })
                payments = register_payment_wizard._create_payments()
                payments_ids.extend(payments.ids)

        if not payments_ids:
            raise UserError(_('No se generaron pagos.'))

        payment_batch = BatchPayment.create({
            'journal_id': self.journal_id.id,
            'payment_method_id': self.payment_method_line_ids[0].payment_method_id.id,
            'payment_ids': [(6, 0, payments_ids)],
            'date': self.payment_date,
        })

        _logger.info("Batch de pagos generado con ID %s", payment_batch.id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Lote de Pagos Generado'),
            'res_model': 'account.batch.payment',
            'res_id': payment_batch.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_enqueue_payment_job(self):
        self.ensure_one()
        AccountMove = self.env['account.move']
        invoices_count = AccountMove.search_count(domain=self.domain_generate_payments())
        if not invoices_count:
            raise UserError(_('No se encontraron Facturas.'))

        # 1) Crear el batch antes de encolar
        BatchPayment = self.env['account.batch.payment']
        batch = BatchPayment.create({
            'journal_id': self.journal_id.id,
            'payment_method_id': self.payment_method_line_ids[0].payment_method_id.id,
            'date': self.payment_date,
            'payment_queue_count': invoices_count,
            'processing_queue': True,
            # payment_ids se dejarán vacíos hasta completar
        })

        BATCH_SIZE = 500
        for method_line in self.payment_method_line_ids:
            invoices = AccountMove.search_read(
                domain=[
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice'),
                    ('payment_state', '=', 'not_paid'),
                    ('preferred_payment_method_line_id', '=', method_line.id),
                    ('company_id', '=', self.env.company.id),
                ],
                fields=['id']
            )

            invoice_ids = [inv['id'] for inv in invoices]

            # 2) Lanzar job async, pasando el batch_id en contexto
            for i in range(0, len(invoice_ids), BATCH_SIZE):
                part = invoice_ids[i:i + BATCH_SIZE]
                self.with_delay(
                    description=_(
                        "Debito automatico lote %(batch)s metodo %(method)s (%(start)s-%(end)s)"
                    ) % {
                        'batch': batch.name,
                        'method': method_line.display_name or method_line.name,
                        'start': i + 1,
                        'end': i + len(part),
                    }
                )._job_generate_payments(part, batch.id, method_line.id)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Procesando...'),
                'message': _(
                    'La generación de pagos fue encolada y se ejecutará en segundo plano, nombre del lote: %s' % batch.name),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _job_generate_payments(self, invoice_ids, batch_id, payment_method_line_id):
        # invoice_ids: lista de IDs de account.move a pagar
        BatchPayment = self.env['account.batch.payment']
        PaymentRegister = self.env['account.payment.register']

        # Recuperar batch desde contexto
        batch_id = batch_id
        if not batch_id:
            _logger.error('Batch ID no encontrado')
            return

        batch = BatchPayment.browse(batch_id)
        if not batch:
            _logger.error('Batch de pago con ID %s no existe', batch_id)
            return

        payments_ids = []
        try:
            register_wizard = PaymentRegister.with_context(
                active_model='account.move',
                active_ids=invoice_ids
            ).create({
                'journal_id': batch.journal_id.id,
                'payment_date': batch.date,
                'payment_method_line_id': payment_method_line_id,
            })
            payments = register_wizard._create_payments()
            payments_ids.extend(payments.ids)

            # Vincular pagos al batch
            batch.write({
                'payment_ids': [(4, pid) for pid in payments_ids],
            })

        except Exception as e:
            # En caso de error cualquier excepción — provoca rollback completo
            _logger.exception('Error generando pagos en cola para batch %s', batch_id)
            # batch.rollback_batch_payments()
            raise

        finally:
            # Siempre, aún en error o éxito, marcar que terminó la cola
            if batch.exists() and batch.payment_queue_count == len(batch.payment_ids):
                _logger.info("Batch de pagos procesado completamente, batch ID %s", batch_id)
