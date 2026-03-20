# -*- coding: utf-8 -*-

import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class MultiInvoicePaymentWizardPOS(models.TransientModel):
    _inherit = 'multi.invoice.payment.wizard'

    def action_generate_payments(self):
        self.ensure_one()

        # === 1. Ejecutar la lógica original para crear todos los pagos ===
        action = super().action_generate_payments()

        # === 2. Filtrar líneas POS del wizard
        pos_lines = self.payment_line_ids.filtered(lambda l: l.payment_method_line_id.payment_method_id.code == 'pos')
        if not pos_lines:
            return action

        for pos_l in pos_lines:
            self._try_poslink_with_rollback(pos_l)

        return action

    def _try_poslink_with_rollback(self, pos_line):
        try:
            payment_ids = pos_line.payment_ids
            self._send_single_pos_transaction(pos_line)
        except Exception as e:
            payment_ids._rollback_payment()
            if 'account.move' in self._context.get('active_model', ''):
                payment_ids.unlink()
            else:
                payment_ids.message_post(body=f"{str(e)}", message_type='comment')
            self.env.cr.commit()
            raise UserError(f"{str(e)}")


    def _send_single_pos_transaction(self, pos_line):
        """Enviar un solo request al POS según las líneas POS del wizard"""
        self.ensure_one()
        provider = self.env['pos.payment.provider'].search([('code', '=', 'poslink')], limit=1)
        if not provider:
            raise UserError(_("No se encontró un proveedor de pago con el código 'poslink'."))
        if not provider.system_id:
            raise UserError(_("El proveedor POS no tiene configurado un ID de sistema."))

        # Terminal del diario de la primera línea
        terminal = pos_line.pos_payment_terminal_id
        if not terminal:
            raise UserError(_("No se encontró terminal POS en la línea."))

        # Datos agregados de las líneas POS
        total_amount = pos_line.amount
        pos_invoice_number = pos_line.pos_invoice_number or self.env['ir.sequence'].next_by_code('pos.invoice.number')

        payment_ids = pos_line.payment_ids
        total_taxable_amount = sum([p.taxable_amount if p.taxable_amount else p.amount for p in payment_ids])
        total_invoice_amount = sum([p.invoice_amount if p.invoice_amount else p.amount for p in payment_ids])

        other_data = {
            "Amount": provider._format_amount_for_pos(total_amount),
            "Quotas": str(pos_line.installment_qty),
            "Plan": str(pos_line.journal_id.plan),
            "Currency": pos_line.currency_id.transact_currency_code,
            "TaxRefund": int(payment_ids[0].tax_refund) if all([payment.tax_refund=='1' for payment in payment_ids]) else 0,
            "InvoiceNumber": pos_invoice_number,
            "NeedToReadCard": pos_line.journal_id.pos_discount_enabled,
            "TaxableAmount": provider._format_amount_for_pos(total_taxable_amount),
            "InvoiceAmount": provider._format_amount_for_pos(total_invoice_amount),
        }

        data = self.env['account.payment']._prepare_pos_request_basic_data(provider, terminal, other_data)

        if not data:
            raise UserError(_("No se pudo preparar la solicitud de envío POS."))

        transaction_number, response_code, response, _ = self.env['account.payment']._pos_transaction_loop_until_final_state(
            provider, terminal, data, 'processFinancialPurchase'
        )

        payment_ids.write({
            'transaction_number': transaction_number,
            'transaction_date_str': response.get('TransactionDate', ''),
            'transaction_state': 'approved',
            'ticket': response.get('Ticket', ''),
            'batch_number': response.get('Batch', ''),
            'pos_invoice_number': response.get('InvoiceNumber', ''),
            'authorization_code': response.get('AuthorizationCode', -1),
            'card_number': response.get('CardNumber', -1),
            'acquirer': response.get('Acquirer', -1),
            'payment_datetime': fields.Datetime.now()
        })

        _logger.info("Transacción POS ejecutada desde wizard múltiple: %s", response)

        # Actualizar log del wizard
        self.log = f"POS transaction #{transaction_number} OK. Código respuesta: {response_code}"
