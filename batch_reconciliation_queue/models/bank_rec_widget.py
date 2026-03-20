# -*- coding: utf-8 -*-
"""
Override bank.rec.widget to detect large batch payments and redirect to queue processing.

When a user attempts to reconcile a batch payment with more than THRESHOLD payments,
instead of processing synchronously (which would timeout on Odoo.sh), we:
1. Create a master reconciliation job
2. Divide the work into chunks
3. Queue chunks for background processing via queue_job
4. Return a notification to the user
"""

import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Threshold for redirecting to queue processing
# Below this, standard Odoo flow is used
DEFAULT_QUEUE_THRESHOLD = 500


class BankRecWidgetQueue(models.Model):
    """
    Override bank.rec.widget to intercept large batch reconciliations.

    Note: bank.rec.widget is a transient model without a real database table
    (_auto = False, _table_query = "0"). This means we cannot use standard
    ORM operations on it for background processing. We intercept the validation
    and create persistent models (batch.reconciliation.master/chunk) to handle
    the actual processing.
    """
    _inherit = 'bank.rec.widget'

    def _get_queue_threshold(self):
        """Get the threshold from system parameter or default."""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'batch_reconciliation_queue.queue_threshold',
            DEFAULT_QUEUE_THRESHOLD
        ))

    def _get_total_batch_payment_count(self, batch_lines):
        """Calculate total number of payments across all batch payment lines."""
        if not batch_lines:
            return 0

        total = 0
        batch_payments = batch_lines.mapped('source_batch_payment_id')

        if batch_payments:
            valid_states = batch_payments._valid_payment_states()
            for bp in batch_payments:
                total += len(bp.payment_ids.filtered(lambda p: p.state in valid_states))

        return total

    def _should_use_queue_processing(self, batch_lines):
        """
        Determine if this reconciliation should use queue processing.

        Returns True if:
        - There are batch payment lines
        - Total payment count exceeds threshold
        """
        if not batch_lines:
            return False

        total_payments = self._get_total_batch_payment_count(batch_lines)
        threshold = self._get_queue_threshold()

        if total_payments >= threshold:
            _logger.info(
                "Large batch detected: %s payments (threshold: %s). Will use queue processing.",
                total_payments, threshold
            )
            return True

        return False

    def _action_validate(self):
        """
        Override to intercept large batch payment reconciliations.

        For batches smaller than threshold: use standard Odoo flow
        For batches >= threshold: create master job and queue for background processing
        """
        self.ensure_one()

        batch_lines = self.line_ids.filtered(lambda x: x.flag == 'new_batch')

        if self._should_use_queue_processing(batch_lines):
            return self._create_queue_reconciliation(batch_lines)

        # Standard flow for small batches
        return super()._action_validate()

    def _create_queue_reconciliation(self, batch_lines):
        """
        Create a master reconciliation job and queue it for processing.

        Args:
            batch_lines: bank.rec.widget.line records with flag='new_batch'

        Returns:
            Action to display notification and navigate to master job
        """
        self.ensure_one()

        total_payments = self._get_total_batch_payment_count(batch_lines)

        _logger.info(
            "Creating queue reconciliation for statement line %s with %s payments",
            self.st_line_id.id, total_payments
        )

        try:
            # Create master job
            MasterModel = self.env['batch.reconciliation.master']
            # Get account from manual operations tab (form_account_id) if defined
            auto_balance_account_id = self.env['account.account']
            for line in self.line_ids:
                if line.flag == 'manual':
                    auto_balance_account_id = line.account_id
            master = MasterModel.create_from_batch_lines(
                self.st_line_id,
                batch_lines,
                auto_balance_account_id=auto_balance_account_id.id
            )

            # Start the job (creates chunks and queues them)
            master.action_start()

            # Return to master form view
            return {
                'type': 'ir.actions.act_window',
                'name': _('Reconciliation Job'),
                'res_model': 'batch.reconciliation.master',
                'res_id': master.id,
                'view_mode': 'form',
                'target': 'current',
            }

        except Exception as e:
            _logger.error("Failed to create queue reconciliation: %s", e, exc_info=True)
            raise UserError(
                _('Failed to create background reconciliation job: %s') % str(e)
            )

    def _validation_lines_vals(self, line_ids_create_command_list, aml_to_exchange_diff_vals, to_reconcile):
        """
        Override to add optimizations for medium-sized batches.

        For batches below queue threshold but still significant (100-500 payments),
        we apply bulk prefetching to improve performance while staying synchronous.
        """
        batch_lines = self.line_ids.filtered(lambda x: x.flag == 'new_batch')

        if batch_lines:
            total_payments = self._get_total_batch_payment_count(batch_lines)

            # For medium batches (100-500), apply prefetch optimization
            if 100 <= total_payments < self._get_queue_threshold():
                _logger.info(
                    "Medium batch detected (%s payments). Applying prefetch optimization.",
                    total_payments
                )
                self._prefetch_batch_data(batch_lines)

        return super()._validation_lines_vals(
            line_ids_create_command_list,
            aml_to_exchange_diff_vals,
            to_reconcile
        )

    def _prefetch_batch_data(self, batch_lines):
        """
        Prefetch data for batch payments to reduce N+1 queries.

        This optimization is applied for medium-sized batches that don't
        require full queue processing but benefit from data prefetching.
        """
        batch_payments = batch_lines.mapped('source_batch_payment_id')
        valid_states = batch_payments._valid_payment_states()

        # Collect all payments
        all_payments = self.env['account.payment']
        for bp in batch_payments:
            all_payments |= bp.payment_ids.filtered(lambda p: p.state in valid_states)

        if not all_payments:
            return

        # Prefetch invoice term lines
        invoice_ids = all_payments.mapped('invoice_ids').ids
        if invoice_ids:
            term_lines = self.env['account.move.line'].search([
                ('move_id', 'in', invoice_ids),
                ('display_type', '=', 'payment_term')
            ], order='date asc')

            # Force into cache
            if term_lines:
                _ = term_lines.mapped('amount_currency')

            _logger.debug(
                "Prefetched %s term lines for %s payments",
                len(term_lines), len(all_payments)
            )
