# -*- coding: utf-8 -*-
"""
Chunk model for processing subsets of payments.

Each chunk processes a manageable number of payments (default 500) independently.
This allows:
- Parallel processing of multiple chunks
- Individual retry on failure
- Progress tracking at granular level
- Compliance with Odoo.sh 15-minute timeout (each chunk < 10 min)
"""

import gc
import json
import logging
import time
from collections import defaultdict

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Processing constants
VALIDATION_BATCH_SIZE = 50  # Payments to validate per batch
COMMIT_INTERVAL = 100  # Commit after processing this many payments
GC_INTERVAL = 200  # Run garbage collection after this many payments


class BatchReconciliationChunk(models.Model):
    """
    Individual chunk of payments to process.

    Each chunk:
    - Contains ~500 payments (configurable)
    - Processes independently as a queue job
    - Creates account.move.line records for its payments
    - Stores reconciliation data for final pairing
    - Can be retried individually on failure
    """
    _name = 'batch.reconciliation.chunk'
    _description = 'Batch Reconciliation Chunk'
    _order = 'master_id, sequence'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    master_id = fields.Many2one(
        'batch.reconciliation.master',
        string='Master Job',
        required=True,
        ondelete='cascade',
        index=True
    )

    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, index=True)

    # Payment data
    payment_ids_json = fields.Text(
        string='Payment IDs',
        default='[]',
        help='JSON array of payment IDs to process in this chunk'
    )
    payment_count = fields.Integer(string='Payment Count', readonly=True)
    processed_payments = fields.Integer(string='Processed Payments', default=0)

    # Results
    created_line_count = fields.Integer(string='Created Lines', default=0)
    reconciled_count = fields.Integer(string='Reconciliation Pairs', default=0)

    # Reconciliation data for final step
    # Format: [[created_line_id, [counterpart_ids]], ...]
    reconciliation_data_json = fields.Text(
        string='Reconciliation Data',
        default='[]'
    )

    # Prepared lines data (created but NOT written to move yet)
    # Format: list of dicts with line_vals and counterpart_ids
    prepared_lines_json = fields.Text(
        string='Prepared Lines Data',
        default='[]',
        help='JSON data of lines to be created by master finalization'
    )

    # Timing
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(
        string='Duration (seconds)',
        compute='_compute_duration',
        store=True
    )

    # Error handling
    error_message = fields.Text(string='Error Message')
    retry_count = fields.Integer(string='Retry Count', default=0)

    # Related fields
    st_line_id = fields.Many2one(
        'account.bank.statement.line',
        related='master_id.st_line_id',
        store=True
    )
    company_id = fields.Many2one(
        'res.company',
        related='master_id.company_id',
        store=True
    )

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for chunk in self:
            if chunk.start_time and chunk.end_time:
                delta = chunk.end_time - chunk.start_time
                chunk.duration = delta.total_seconds()
            else:
                chunk.duration = 0.0

    def _get_payments(self):
        """Get payments from JSON field."""
        self.ensure_one()
        try:
            ids = json.loads(self.payment_ids_json or '[]')
            return self.env['account.payment'].browse(ids).exists()
        except (json.JSONDecodeError, TypeError):
            return self.env['account.payment']

    # =========================================================================
    # Main Processing Method
    # =========================================================================

    def action_process(self):
        """
        Process this chunk of payments.

        This is the main entry point called by queue_job.
        It processes all payments in the chunk and creates the necessary
        account.move.line records.
        """
        self.ensure_one()

        if self.state not in ('pending', 'failed'):
            _logger.warning("Chunk %s cannot be processed (state=%s)", self.id, self.state)
            return False

        _logger.info("Starting chunk %s processing (%s payments)",
                     self.id, self.payment_count)

        start = time.time()

        self.write({
            'state': 'processing',
            'start_time': fields.Datetime.now(),
            'error_message': False,
        })
        # NOTE: Do NOT commit here - queue_job manages transactions via savepoints

        try:
            # Process the payments
            result = self._process_payments()

            elapsed = time.time() - start

            self.write({
                'state': 'done',
                'end_time': fields.Datetime.now(),
                'processed_payments': self.payment_count,
                'created_line_count': result['prepared_lines'],
                'reconciled_count': result['reconcile_pairs'],
                'prepared_lines_json': json.dumps(result['prepared_data']),
            })

            _logger.info(
                "Chunk %s completed in %.2fs: %s lines prepared, %s reconcile pairs",
                self.id, elapsed, result['prepared_lines'], result['reconcile_pairs']
            )

            # NOTE: Do NOT commit here - queue_job commits on success
            return True

        except Exception as e:
            _logger.error("Chunk %s failed: %s", self.id, e, exc_info=True)
            # NOTE: Do NOT write state here - let queue_job handle failure
            # The job will be marked as failed by queue_job and can be retried
            raise

    def _process_payments(self):
        """
        Process all payments in this chunk.

        NOTE: This method NO LONGER writes to the move directly.
        Instead, it prepares the line data which will be written
        by the master's finalization step. This avoids conflicts
        when multiple chunks run in parallel.

        Returns:
            dict with:
                - prepared_lines: count of prepared move lines
                - reconcile_pairs: count of reconciliation pairs
                - prepared_data: list of dicts with line_vals and counterpart_ids
        """
        self.ensure_one()

        payments = self._get_payments()
        if not payments:
            return {
                'prepared_lines': 0,
                'reconcile_pairs': 0,
                'prepared_data': []
            }

        st_line = self.st_line_id
        move = st_line.move_id

        if not move:
            raise UserError(_('Statement line has no associated move.'))

        # Step 1: Bulk prefetch invoice term lines
        _logger.debug("Chunk %s: Prefetching invoice term lines", self.id)
        self._bulk_prefetch_invoice_term_lines(payments)

        # Step 2: Validate unvalidated payments
        unvalidated = payments.filtered(lambda p: not p.move_id or p.state == 'draft')
        if unvalidated:
            _logger.debug("Chunk %s: Validating %s payments", self.id, len(unvalidated))
            self._bulk_validate_payments(unvalidated)
            # Invalidate cache to ensure move_id is refreshed after validation
            payments.invalidate_recordset(['move_id', 'state'])

        # Step 3: Get reference data
        company_currency = self.company_id.currency_id

        # Step 4: Prepare payment lines data (NOT writing to move)
        result = self._prepare_payment_lines(
            payments,
            company_currency
        )

        return result

    def _bulk_prefetch_invoice_term_lines(self, payments):
        """
        Bulk prefetch all invoice term lines in a single query.

        This eliminates the N+1 query problem where standard flow
        would execute one query per payment.
        """
        if not payments:
            return

        # Get all invoice IDs linked to payments
        invoice_ids = []
        for payment in payments:
            invoice_ids.extend(payment.invoice_ids.ids)

        if not invoice_ids:
            return

        # Remove duplicates
        invoice_ids = list(set(invoice_ids))

        # Single query to load all term lines into cache
        term_lines = self.env['account.move.line'].search([
            ('move_id', 'in', invoice_ids),
            ('display_type', '=', 'payment_term')
        ], order='date asc')

        # Force load into ORM cache
        if term_lines:
            _ = term_lines.mapped('amount_currency')

        _logger.debug(
            "Prefetched %s term lines from %s invoices",
            len(term_lines), len(invoice_ids)
        )

    def _bulk_validate_payments(self, payments):
        """
        Validate payments in batches to avoid memory issues.
        """
        total = len(payments)

        for i in range(0, total, VALIDATION_BATCH_SIZE):
            batch = payments[i:i + VALIDATION_BATCH_SIZE]

            try:
                batch.action_post()
            except Exception as e:
                _logger.error(
                    "Failed to validate payments %s-%s: %s",
                    i, i + len(batch), e
                )
                raise

            # Clean up periodically (no commit - queue_job manages transactions)
            if i > 0 and i % (VALIDATION_BATCH_SIZE * 4) == 0:
                gc.collect()

    def _prepare_payment_lines(self, payments, company_currency):
        """
        Prepare account.move.line data for all payments WITHOUT writing to the move.

        The actual write is done by the master's finalization step to avoid
        conflicts when multiple chunks run in parallel.

        IMPORTANT: Following standard Odoo pattern from account_accountant_batch_payment:
        - For payments WITH move_id (already validated): use liquidity_lines from payment
        - For payments WITHOUT move_id (draft with invoices): use unreconciled term_lines

        Returns:
            dict with prepared_lines count, reconcile_pairs count, and prepared_data
        """
        prepared_data = []
        processed = 0

        # Get the default AMLs matching domain from the statement line
        st_line = self.st_line_id
        amls_domain = st_line._get_default_amls_matching_domain()

        for payment in payments:
            if payment.move_id:
                # Payment is already validated - use LIQUIDITY LINES
                # This is the correct approach per standard Odoo
                payment_lines_data = self._prepare_validated_payment_lines(
                    payment, company_currency, amls_domain
                )
            else:
                # Payment has no move but has invoices - use unreconciled term lines
                # This handles the edge case of draft payments in batch
                payment_lines_data = self._prepare_draft_payment_lines(
                    payment, company_currency
                )

            prepared_data.extend(payment_lines_data)
            processed += 1

            # Periodic cleanup
            if processed % COMMIT_INTERVAL == 0:
                _logger.debug("Chunk %s: Prepared %s/%s payments",
                             self.id, processed, len(payments))

            if processed % GC_INTERVAL == 0:
                gc.collect()

        _logger.debug("Chunk %s: Prepared %s lines from %s payments",
                     self.id, len(prepared_data), len(payments))

        return {
            'prepared_lines': len(prepared_data),
            'reconcile_pairs': len([d for d in prepared_data if d['counterpart_ids']]),
            'prepared_data': prepared_data,
        }

    def _prepare_validated_payment_lines(self, payment, company_currency, amls_domain):
        """
        Prepare line data for a payment that is already validated (has move_id).

        Following standard Odoo pattern: use the LIQUIDITY LINES from the payment,
        which are in the outstanding account (e.g., 110200 Outstanding Receipts).
        These are the lines that need to be reconciled with the bank statement.

        Args:
            payment: account.payment record (already validated)
            company_currency: res.currency of the company
            amls_domain: domain for filtering valid AMLs

        Returns:
            list of dicts with line_vals and counterpart_ids
        """
        prepared_data = []

        # Get liquidity lines using Odoo's standard method
        # _seek_for_lines returns: (liquidity_lines, counterpart_lines, writeoff_lines)
        liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()

        # Filter by the matching domain (ensures currency, state, etc. are valid)
        valid_liquidity_lines = liquidity_lines.filtered_domain(amls_domain)

        # Additionally filter out lines with no residual (already fully reconciled)
        valid_liquidity_lines = valid_liquidity_lines.filtered(
            lambda l: not l.currency_id.is_zero(l.amount_residual_currency)
            or not l.company_currency_id.is_zero(l.amount_residual)
        )

        for liq_line in valid_liquidity_lines:
            # The line in the statement move should be the inverse of the liquidity line
            # to cancel out the outstanding account
            line_vals = {
                'name': payment.name or payment.ref or liq_line.name or '',
                'partner_id': payment.partner_id.id,
                'account_id': liq_line.account_id.id,
                'currency_id': liq_line.currency_id.id,
                'amount_currency': -liq_line.amount_residual_currency,
                'balance': -liq_line.amount_residual,
            }

            prepared_data.append({
                'line_vals': line_vals,
                'counterpart_ids': [liq_line.id],  # Reconcile with the liquidity line
            })

        return prepared_data

    def _prepare_draft_payment_lines(self, payment, company_currency):
        """
        Prepare line data for a payment without move_id (draft payment with invoices).

        Following standard Odoo pattern: use UNRECONCILED term lines from invoices.
        This is only for edge cases where payments are still in draft state.

        Args:
            payment: account.payment record (draft, no move_id)
            company_currency: res.currency of the company

        Returns:
            list of dicts with line_vals and counterpart_ids
        """
        prepared_data = []

        if not payment.invoice_ids:
            # No invoices linked - use partner's default account
            partner_account = (
                payment.partner_id.property_account_payable_id
                if payment.payment_type == 'outbound'
                else payment.partner_id.property_account_receivable_id
            )

            balance = payment.currency_id._convert(
                from_amount=-payment.amount_signed,
                to_currency=company_currency,
                company=self.company_id,
                date=payment.date,
            )

            line_vals = {
                'name': payment.name or payment.ref or '',
                'partner_id': payment.partner_id.id,
                'account_id': partner_account.id,
                'currency_id': payment.currency_id.id,
                'amount_currency': -payment.amount_signed,
                'balance': balance,
            }

            prepared_data.append({
                'line_vals': line_vals,
                'counterpart_ids': [],
            })
            return prepared_data

        # Get UNRECONCILED term lines from invoices (key filter: not l.reconciled)
        term_lines = payment.invoice_ids.line_ids.filtered(
            lambda l: l.display_type == 'payment_term' and not l.reconciled
        ).sorted('date')

        if not term_lines:
            _logger.warning(
                "Payment %s has invoices but no unreconciled term lines",
                payment.id
            )
            return prepared_data

        account2amount = defaultdict(float)
        account2lines = defaultdict(list)

        term_lines_iter = iter(term_lines)
        remaining = payment.amount_signed
        select_amount_func = min if payment.payment_type == 'inbound' else max

        # Allocate payment amount to unreconciled term lines
        while remaining:
            term_line = next(term_lines_iter, None)
            if not term_line:
                break

            # Convert term line amount to payment currency
            term_amount = term_line.currency_id._convert(
                from_amount=term_line.amount_currency,
                to_currency=payment.currency_id,
                company=self.company_id,
                date=payment.date,
            )

            current = select_amount_func(remaining, term_amount)
            remaining -= current
            account2amount[term_line.account_id] -= current
            account2lines[term_line.account_id].append(term_line.id)

        # Handle any remaining amount (excess payment)
        if remaining:
            partner_account = (
                payment.partner_id.property_account_payable_id
                if payment.payment_type == 'outbound'
                else payment.partner_id.property_account_receivable_id
            )
            account2amount[partner_account] -= remaining

        # Prepare line data for each account
        for account, amount in account2amount.items():
            balance = payment.currency_id._convert(
                from_amount=amount,
                to_currency=company_currency,
                company=self.company_id,
                date=payment.date,
            )

            line_vals = {
                'name': payment.name or payment.ref or '',
                'partner_id': payment.partner_id.id,
                'account_id': account.id,
                'currency_id': payment.currency_id.id,
                'amount_currency': amount,
                'balance': balance,
            }

            counterpart_ids = account2lines.get(account, [])

            prepared_data.append({
                'line_vals': line_vals,
                'counterpart_ids': counterpart_ids,
            })

        return prepared_data

    # =========================================================================
    # User Actions
    # =========================================================================

    def action_retry(self):
        """Retry a failed chunk."""
        self.ensure_one()

        if self.state != 'failed':
            raise UserError(_('Only failed chunks can be retried.'))

        self.write({
            'state': 'pending',
            'error_message': False,
            'start_time': False,
            'end_time': False,
            'processed_payments': 0,
            'created_line_count': 0,
            'reconciled_count': 0,
            'reconciliation_data_json': '[]',
            'prepared_lines_json': '[]',
        })

        # Queue for processing
        self.delayable(
            priority=5,
            max_retries=3,
            description=_('Retry chunk: %s') % self.name,
            channel='root.reconciliation',
        ).action_process().delay()

        return True

    def action_cancel(self):
        """Cancel a pending chunk."""
        self.ensure_one()

        if self.state not in ('pending', 'failed'):
            raise UserError(_('Only pending or failed chunks can be cancelled.'))

        self.write({
            'state': 'cancelled',
            'end_time': fields.Datetime.now(),
        })

        return True

    def action_view_master(self):
        """Navigate to the master job."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Master Job'),
            'res_model': 'batch.reconciliation.master',
            'res_id': self.master_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
