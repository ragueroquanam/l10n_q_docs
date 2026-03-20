# -*- coding: utf-8 -*-

import logging
from _datetime import datetime
from odoo import fields, models, _
from odoo.exceptions import UserError

from odoo.addons.pos_link_q.models.abstract_pos_link_mixin import AbstractPosLinkMixin

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model, AbstractPosLinkMixin):
    _inherit = 'account.payment'

    is_voided = fields.Boolean(string="Anulado o devuelto?", copy=False)
    void_type = fields.Selection([
        ('cancel', 'Anulación'),
        ('refund', 'Devolución')
    ], string="Tipo de operación", copy=False)
    voided_transaction_id = fields.Char(string="ID de Transacción", copy=False)

    def action_open_void_wizard(self):
        self.ensure_one()
        if not self.is_pos_method or self.state != 'in_process':
            raise UserError(_("The payment is not a POS payment in process."))
        return {
            'name': _("Void / Refund POS Payment"),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.void.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payment_id': self.id},
        }

    def convert_ddmmaa_to_aammdd(self, transaction_date_str):
        """
        Convierte una fecha en formato DDMMAA a AAMMDD.
        Ejemplo: '020725' -> '250702'
        """
        if not transaction_date_str or len(transaction_date_str) != 6:
            return ''
        dia = transaction_date_str[:2]
        mes = transaction_date_str[2:4]
        anio = transaction_date_str[4:]
        return f"{anio}{mes}{dia}"

    def process_pos_void(self, manual):
        self.ensure_one()
        if manual:
            self.write({'state': 'canceled', 'is_voided': True})
        else:
            provider = self.env['pos.payment.provider'].search([('code', '=', 'poslink')], limit=1)
            if not provider:
                raise UserError(_("No se encontró un proveedor de pago con el código 'poslink'."))
            if not provider.system_id:
                raise UserError(_("No se encontró un Id de sistema en el proveedor de pago con el código 'poslink'."))
            if not self.pos_payment_terminal_id:
                raise UserError(_("No se encontró un terminal de pago POS asociado al pago."))
            if not self.transaction_number:
                raise UserError(_("No se encontró un Nro. de Transacción asociado al pago."))

            terminal = self.pos_payment_terminal_id
            transaction_number = int(self.transaction_number)
            clean_ticket = self.ticket.replace("(", "").replace(")", "").replace(",", "").replace("'", "").strip()
            request_data = self._prepare_pos_request_BatchQuery(provider, terminal, {})
            request_response, request_code = self._execute_pos_transaction(provider, "processCurrentTransactionsBatchQuery", request_data,
                                                                           success_codes=[0, 110])

            transactions = request_response.get('QueryTransactionsCurrentBatchTransaction', [])
            void_type = None
            response = None
            for tx in transactions:
                if tx.get('TransactionId') == transaction_number:
                    # Reverso de anulación
                    other_data = {
                        "TicketNumber": self.ticket,
                        "Acquirer": self.acquirer,
                    }
                    request_data = self._prepare_pos_request_processFinancialPurchaseVoidByTicket(provider, terminal,
                                                                                                  other_data)
                    transaction_number, response_code, response, process_reverse = self._pos_transaction_loop_until_final_state(
                        provider, terminal, request_data, 'processFinancialPurchaseVoidByTicket')
                    void_type = 'cancel'
                    _logger.info("Reverso de anulación POS: %s", response)
                    break

            if not void_type:
                # Reverso de Devolucion
                transaction_number, response_code, response, process_reverse = self._pos_reverse_refund(provider,
                                                                                                        terminal,
                                                                                                        clean_ticket)
                void_type = 'refund'

            return response, transaction_number, void_type

    def _pos_reverse_refund(self, provider, terminal, clean_ticket):
        """Realiza el reverso de devolución POS y retorna la respuesta."""
        self.ensure_one()
        clean_invoice_number = self.pos_invoice_number.replace("(", "").replace(")", "").replace(",", "").replace("'",

                                                                                                                  "").strip()
        all_payments = self.get_related_payments()
        amount = sum(all_payments.mapped('amount'))
        other_data = {
            "OriginalTransactionDateyyMMdd": self.convert_ddmmaa_to_aammdd(self.transaction_date_str),
            "Amount": provider._format_amount_for_pos(amount),
            "Currency": self.currency_id.transact_currency_code,
            "Quotas": self.installment_qty,
            "Plan": self.journal_id.plan,
            "TaxableAmount": provider._format_amount_for_pos(amount),
            "TaxRefund": int(self.tax_refund) if self.tax_refund else 0,
            "InvoiceAmount": provider._format_amount_for_pos(amount),
            "InvoiceNumber": clean_invoice_number,
            # "CiNoCheckDigict": "4795307",
            # "Merchant": "20523072",
            "NeedToReadCard": self.pos_discount_enabled,
            "TicketNumber": clean_ticket
        }
        request_data = self._prepare_pos_request_processFinancialPurchaseRefund(provider, terminal, other_data)
        transaction_number, response_code, response, process_reverse = self._pos_transaction_loop_until_final_state(
            provider, terminal, request_data, 'processFinancialPurchaseRefund')
        _logger.info("Reverso de Devolución POS: %s", response)
        return transaction_number, response_code, response, process_reverse

    def get_related_payments(self):
        """
        Returns related payments with the same transaction_number and the union with the current payment.
        """
        related_payments = self.env['account.payment'].search([
            ('transaction_number', '=', self.transaction_number),
            ('id', '!=', self.id)
        ])
        all_payments = self | related_payments
        return all_payments

    def handle_pos_void_response(self, response, trans_id, void_type):
        self.ensure_one()
        code = response.get('PosResponseCode')
        if code == "00":
            # Buscar otros pagos con el mismo transaction_number
            all_payments = self.get_related_payments()
            all_payments.write({
                'void_type': void_type,
                'is_voided': True,
                'voided_transaction_id': trans_id,
            })
            all_payments.action_cancel()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'message': _("El cliente recibirá la devolución entre 48 y 72 horas."),
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        else:
            return {'type': 'ir.actions.act_window_close'}

    def action_manual_refund(self):
        return self.env['base.wizard'].launch_wizard(
            env=self.env,
            model_name='account.payment',
            method_name='action_manual_refund_wizard',
            active_ids=self.ids,
            show_fields=['base_char'],
            default_fields={'base_char': ''},
            label_map={'base_char': 'ID de Transacción'},
            wizard_name='Devolución Manual',
        )

    def action_manual_refund_wizard(self, values):
        self.write({
            'voided_transaction_id': values.get('base_char'),
            'is_voided': True,
            'void_type': 'refund'
        })
        return self.action_cancel()

    def action_manual_cancel(self):
        return self.env['base.wizard'].launch_wizard(
            env=self.env,
            model_name='account.payment',
            method_name='action_manual_cancel_wizard',
            active_ids=self.ids,
            show_fields=['base_char'],
            default_fields={'base_char': ''},
            label_map={'base_char': 'ID de Transacción'},
            wizard_name='Anulación Manual',
        )

    def action_manual_cancel_wizard(self, values):
        self.write({
            'voided_transaction_id': values.get('base_char'),
            'is_voided': True,
            'void_type': 'cancel'
        })
        return self.action_cancel()

    def action_post(self):
        if self._context.get('skip_pos_request'):
            return super().action_post()
        if all(rec.payment_method_line_id.code == 'pos' for rec in self) and all(
                rec.state == 'draft' for rec in self) and all(
            rec.transaction_state not in ('sent', 'approved') for rec in self):
            self._try_poslink_with_rollback()
        return super().action_post()

    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        if self._context.get('skip_pos_request'):
            return super()._generate_journal_entry(write_off_line_vals, force_balance, line_ids)
        if (self.state == 'draft' and 'account.move' in self._context.get('active_model', '') and
                self.payment_method_line_id.code == 'pos' and
                all(rec.transaction_state not in ('sent', 'approved') for rec in self)):
            self._try_poslink_with_rollback()
        return super(AccountPayment, self)._generate_journal_entry(write_off_line_vals, force_balance, line_ids)

    def _try_poslink_with_rollback(self):
        try:
            self._pos_link_purchase_request()
        except Exception as e:
            self._rollback_payment()
            if 'account.move' in self._context.get('active_model', ''):
                self.unlink()
            else:
                self.message_post(body=f"{str(e)}", message_type='comment')
            self.env.cr.commit()
            raise UserError(f"{str(e)}")

    def _rollback_payment(self):
        """
        Revierte el pago creado si ocurre un error con la integración POS.
        """
        for payment in self:
            if payment.state != 'draft':
                payment.action_draft()
        self.write({'transaction_state': 'error'})

    def _pos_link_purchase_request(self):
        provider = self.env['pos.payment.provider'].search([('code', '=', 'poslink')], limit=1)
        if not provider:
            raise UserError(_("No se encontró un proveedor de pago con el código 'poslink'."))
        if not provider.system_id:
            raise UserError(_("No se encontró un Id de sistema en el proveedor de pago con el código 'poslink'."))
        if not self.pos_payment_terminal_id:
            raise UserError(_("No se encontró un terminal de pago POS asociado al pago."))

        # Datos de referencia (todos deben compartir plan, terminal, moneda, etc.)
        ref_payment = self[0]
        total_amount = sum(rec.amount for rec in self)
        total_taxable_amount = ref_payment.taxable_amount
        total_invoice_amount = ref_payment.invoice_amount
        pos_invoice_number = ref_payment.pos_invoice_number
        if not pos_invoice_number:
            seq = self.env['ir.sequence'].next_by_code('pos.invoice.number')
            pos_invoice_number = str(seq).zfill(7) if seq else ''

        other_data = {
            "Amount": provider._format_amount_for_pos(total_amount),
            "Quotas": str(ref_payment.installment_qty),
            "Plan": str(ref_payment.journal_id.plan),
            "Currency": ref_payment.currency_id.transact_currency_code,
            "TaxRefund": int(ref_payment.tax_refund) if ref_payment.tax_refund else 0,
            "InvoiceNumber": pos_invoice_number,
            "NeedToReadCard": ref_payment.journal_id.pos_discount_enabled,
            "TaxableAmount": provider._format_amount_for_pos(
                (total_taxable_amount if total_taxable_amount else total_amount)),
            "InvoiceAmount": provider._format_amount_for_pos(
                (total_invoice_amount if total_invoice_amount else total_amount)),
        }

        terminal = ref_payment.pos_payment_terminal_id
        data = self._prepare_pos_request_basic_data(provider, terminal, other_data)
        if data:
            self.write({'transaction_state': 'sent'})
            transaction_number, response_code, response, process_reverse = self._pos_transaction_loop_until_final_state(
                provider, terminal, data, 'processFinancialPurchase')

            self.write({
                'transaction_number': transaction_number,
                'transaction_date_str': response.get('TransactionDate', ''),
                'transaction_state': 'approved',
                'ticket': response.get('Ticket', ''),
                'batch_number': response.get('Batch', ''),
                'pos_invoice_number': response.get('InvoiceNumber', ''),
                'authorization_code': response.get('AuthorizationCode', -1),
                'card_number': response.get('CardNumber', -1),
                'acquirer': response.get('Acquirer', -1),
                # 'tax_refund': response.get('TaxRefund', ''),
                'payment_datetime': fields.Datetime.now()
            })

        _logger.info("Respuesta del proveedor POS: %s", response)
