# -*- coding: utf-8 -*-
"""
Master model for coordinating large batch reconciliation jobs.

This model orchestrates the entire reconciliation process by:
1. Dividing work into chunks of manageable size
2. Creating and tracking chunk jobs
3. Coordinating final reconciliation when all chunks complete
4. Handling errors and retries at chunk level
"""

import json
import logging
from collections import defaultdict
from datetime import datetime

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Configuration constants - can be overridden via system parameters
DEFAULT_CHUNK_SIZE = 500  # Payments per chunk
DEFAULT_MAX_PARALLEL_CHUNKS = 3  # Maximum concurrent chunk jobs
DEFAULT_JOB_TIMEOUT = 600  # 10 minutes per chunk max


class BatchReconciliationMaster(models.Model):
    """
    Master record for coordinating batch reconciliation.

    One master is created per reconciliation request. The master:
    - Divides payments into chunks
    - Creates chunk records for each subset
    - Tracks overall progress
    - Handles final reconciliation when all chunks complete
    """
    _name = 'batch.reconciliation.master'
    _description = 'Batch Reconciliation Master'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Identification
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        default=lambda self: _('New')
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('preparing', 'Preparing Chunks'),
        ('processing', 'Processing Chunks'),
        ('lines_created', 'Lines Created'),
        ('reconciling', 'Reconciling'),
        ('reconciled', 'Reconciled'),
        ('done', 'Completed'),  # Kept for backwards compatibility
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    # References
    st_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Bank Statement Line',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='st_line_id.company_id',
        store=True
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        related='st_line_id.journal_id',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='st_line_id.currency_id',
        store=True
    )

    # Batch payment data (stored as JSON for flexibility)
    batch_payment_ids_json = fields.Text(
        string='Batch Payment IDs',
        default='[]',
        help='JSON array of batch payment IDs to process'
    )
    batch_payment_names = fields.Char(
        string='Batch Payments',
        compute='_compute_batch_payment_names'
    )

    # Chunks
    chunk_ids = fields.One2many(
        'batch.reconciliation.chunk',
        'master_id',
        string='Processing Chunks'
    )

    # Configuration
    chunk_size = fields.Integer(
        string='Chunk Size',
        default=DEFAULT_CHUNK_SIZE,
        help='Number of payments to process per chunk'
    )
    max_parallel_chunks = fields.Integer(
        string='Max Parallel Chunks',
        default=DEFAULT_MAX_PARALLEL_CHUNKS,
        help='Maximum number of chunks to process in parallel'
    )

    # Progress tracking
    total_payments = fields.Integer(string='Total Payments', readonly=True)
    processed_payments = fields.Integer(
        string='Processed Payments',
        compute='_compute_progress',
        store=True
    )
    progress = fields.Float(
        string='Progress %',
        compute='_compute_progress',
        store=True
    )
    total_chunks = fields.Integer(
        string='Total Chunks',
        compute='_compute_chunk_stats',
        store=True
    )
    completed_chunks = fields.Integer(
        string='Completed Chunks',
        compute='_compute_chunk_stats',
        store=True
    )
    failed_chunks = fields.Integer(
        string='Failed Chunks',
        compute='_compute_chunk_stats',
        store=True
    )

    # Timing
    start_time = fields.Datetime(string='Start Time', readonly=True)
    end_time = fields.Datetime(string='End Time', readonly=True)
    duration = fields.Float(
        string='Duration (seconds)',
        compute='_compute_duration',
        store=True
    )

    # Results
    created_move_line_count = fields.Integer(
        string='Created Move Lines',
        readonly=True,
        default=0
    )
    reconciled_aml_count = fields.Integer(
        string='Reconciled AMLs',
        readonly=True,
        default=0
    )
    error_message = fields.Text(string='Error Message', tracking=True)
    auto_balance_account_id = fields.Many2one(
        'account.account',
        string='Auto-balance Account',
        help='Account from manual operations tab, used for auto-balance line'
    )

    # Move reference (created during lines_created phase)
    reconciliation_move_id = fields.Many2one(
        'account.move',
        string='Reconciliation Move',
        readonly=True,
        help='The account move where reconciliation lines are created'
    )

    # Reconciliation plan and progress
    reconciliation_plan_json = fields.Text(
        string='Reconciliation Plan',
        readonly=True,
        help='JSON with line sequences and counterpart IDs for deferred reconciliation'
    )
    total_pairs_to_reconcile = fields.Integer(
        string='Total Pairs to Reconcile',
        readonly=True,
        default=0
    )
    reconciled_pairs_count = fields.Integer(
        string='Reconciled Pairs',
        readonly=True,
        default=0
    )
    last_reconciled_index = fields.Integer(
        string='Last Reconciled Index',
        readonly=True,
        default=0,
        help='Index of the last reconciled pair, for resuming'
    )
    reconciliation_batch_size = fields.Integer(
        string='Reconciliation Batch Size',
        default=100,
        help='Number of pairs to reconcile per batch operation'
    )
    reconciliation_progress = fields.Float(
        string='Reconciliation Progress %',
        compute='_compute_reconciliation_progress',
        store=True
    )
    auto_reconcile_queued = fields.Boolean(
        string='Auto-Reconcile Queued',
        default=False,
        help='True if reconciliation is running via queue_job'
    )
    reconciliation_start_time = fields.Datetime(
        string='Reconciliation Start Time',
        readonly=True
    )
    reconciliation_end_time = fields.Datetime(
        string='Reconciliation End Time',
        readonly=True
    )

    # Queue job reference
    queue_job_ids = fields.Many2many(
        'queue.job',
        string='Queue Jobs',
        compute='_compute_queue_jobs'
    )

    @api.depends('batch_payment_ids_json')
    def _compute_batch_payment_names(self):
        for master in self:
            batch_payments = master._get_batch_payments()
            master.batch_payment_names = ', '.join(batch_payments.mapped('name')) if batch_payments else ''

    @api.depends('chunk_ids.state', 'chunk_ids.processed_payments')
    def _compute_progress(self):
        for master in self:
            if master.total_payments > 0:
                processed = sum(master.chunk_ids.filtered(
                    lambda c: c.state == 'done'
                ).mapped('payment_count'))
                master.processed_payments = processed
                master.progress = (processed / master.total_payments) * 100
            else:
                master.processed_payments = 0
                master.progress = 0.0

    @api.depends('chunk_ids', 'chunk_ids.state')
    def _compute_chunk_stats(self):
        for master in self:
            chunks = master.chunk_ids
            master.total_chunks = len(chunks)
            master.completed_chunks = len(chunks.filtered(lambda c: c.state == 'done'))
            master.failed_chunks = len(chunks.filtered(lambda c: c.state == 'failed'))

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for master in self:
            if master.start_time and master.end_time:
                delta = master.end_time - master.start_time
                master.duration = delta.total_seconds()
            else:
                master.duration = 0.0

    @api.depends('reconciled_pairs_count', 'total_pairs_to_reconcile')
    def _compute_reconciliation_progress(self):
        for master in self:
            if master.total_pairs_to_reconcile > 0:
                master.reconciliation_progress = (
                    master.reconciled_pairs_count / master.total_pairs_to_reconcile
                ) * 100
            else:
                master.reconciliation_progress = 0.0

    def _compute_queue_jobs(self):
        """Find related queue jobs."""
        QueueJob = self.env['queue.job'].sudo()
        for master in self:
            jobs = QueueJob.search([
                ('model_name', '=', 'batch.reconciliation.master'),
                ('records', 'like', f'%{master.id}%'),
            ])
            chunk_jobs = QueueJob.search([
                ('model_name', '=', 'batch.reconciliation.chunk'),
                ('records', 'like', f'%{master.chunk_ids.ids}%'),
            ]) if master.chunk_ids else QueueJob
            master.queue_job_ids = jobs | chunk_jobs

    def _get_batch_payments(self):
        """Get batch payments from JSON field."""
        self.ensure_one()
        try:
            ids = json.loads(self.batch_payment_ids_json or '[]')
            return self.env['account.batch.payment'].browse(ids).exists()
        except (json.JSONDecodeError, TypeError):
            return self.env['account.batch.payment']

    def _set_batch_payments(self, batch_payments):
        """Set batch payments to JSON field."""
        self.ensure_one()
        if batch_payments:
            self.batch_payment_ids_json = json.dumps(batch_payments.ids)
        else:
            self.batch_payment_ids_json = '[]'

    @api.model
    def _get_chunk_size(self):
        """Get chunk size from system parameter or default."""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'batch_reconciliation_queue.chunk_size',
            DEFAULT_CHUNK_SIZE
        ))

    @api.model
    def _get_max_parallel_chunks(self):
        """Get max parallel chunks from system parameter or default."""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'batch_reconciliation_queue.max_parallel_chunks',
            DEFAULT_MAX_PARALLEL_CHUNKS
        ))

    @api.model
    def _get_reconciliation_batch_size(self):
        """Get reconciliation batch size from system parameter or default."""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'batch_reconciliation_queue.reconciliation_batch_size',
            100
        ))

    # =========================================================================
    # Main Entry Point
    # =========================================================================

    @api.model
    def create_from_batch_lines(self, st_line, batch_lines, auto_balance_account_id=False):
        """
        Create a master reconciliation job from batch payment lines.

        This is the main entry point called from bank.rec.widget when
        a large batch payment reconciliation is detected.

        Args:
            st_line: account.bank.statement.line record
            batch_lines: bank.rec.widget.line records with flag='new_batch'
            auto_balance_account_id: account.account ID from manual operations tab

        Returns:
            batch.reconciliation.master record
        """
        batch_payments = batch_lines.mapped('source_batch_payment_id')

        if not batch_payments:
            raise UserError(_('No batch payments found in the selection.'))

        # Calculate total payments
        valid_states = batch_payments._valid_payment_states()
        total_payments = sum(
            len(bp.payment_ids.filtered(lambda p: p.state in valid_states))
            for bp in batch_payments
        )

        # Create master record
        master = self.create({
            'name': _('Reconciliation - %s - %s payments') % (
                st_line.name or st_line.payment_ref or 'New',
                total_payments
            ),
            'st_line_id': st_line.id,
            'total_payments': total_payments,
            'chunk_size': self._get_chunk_size(),
            'max_parallel_chunks': self._get_max_parallel_chunks(),
            'reconciliation_batch_size': self._get_reconciliation_batch_size(),
            'auto_balance_account_id': auto_balance_account_id,
        })
        master._set_batch_payments(batch_payments)

        _logger.info(
            "Created master reconciliation job %s for %s payments from %s batches",
            master.id, total_payments, len(batch_payments)
        )

        return master

    def action_start(self):
        """Start the reconciliation process."""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_('Only draft masters can be started.'))

        self.write({
            'state': 'preparing',
            'start_time': fields.Datetime.now(),
            'error_message': False,
        })

        try:
            # Step 1: Create chunks
            self._create_chunks()

            # Step 2: Queue the chunks for processing
            self._queue_chunks()

            self.write({'state': 'processing'})
            self.env.cr.commit()

            _logger.info("Master %s started with %s chunks", self.id, self.total_chunks)

            return self._get_notification_action(
                _('Reconciliation Started'),
                _('Processing %s payments in %s chunks. You will be notified when complete.') % (
                    self.total_payments, self.total_chunks
                ),
                'info'
            )

        except Exception as e:
            _logger.error("Failed to start master %s: %s", self.id, e, exc_info=True)
            self.write({
                'state': 'failed',
                'error_message': str(e),
                'end_time': fields.Datetime.now(),
            })
            raise

    def _create_chunks(self):
        """
        Divide the total payments into chunks for parallel processing.

        Each chunk will be processed as an independent job, allowing:
        - Parallel execution
        - Individual retry on failure
        - Progress tracking at chunk level
        """
        self.ensure_one()

        batch_payments = self._get_batch_payments()
        valid_states = batch_payments._valid_payment_states()

        # Collect all payments
        all_payments = self.env['account.payment']
        for bp in batch_payments:
            all_payments |= bp.payment_ids.filtered(lambda p: p.state in valid_states)

        if not all_payments:
            raise UserError(_('No valid payments found in the batch payments.'))

        _logger.info("Creating chunks for %s payments (chunk_size=%s)",
                     len(all_payments), self.chunk_size)

        # Create chunks
        chunk_number = 0
        ChunkModel = self.env['batch.reconciliation.chunk']

        for i in range(0, len(all_payments), self.chunk_size):
            chunk_payments = all_payments[i:i + self.chunk_size]
            chunk_number += 1

            ChunkModel.create({
                'name': _('Chunk %s/%s') % (
                    chunk_number,
                    (len(all_payments) + self.chunk_size - 1) // self.chunk_size
                ),
                'master_id': self.id,
                'sequence': chunk_number,
                'payment_ids_json': json.dumps(chunk_payments.ids),
                'payment_count': len(chunk_payments),
                'state': 'pending',
            })

        _logger.info("Created %s chunks for master %s", chunk_number, self.id)

    def _queue_chunks(self):
        """
        Queue chunks for processing using queue_job.

        Uses a chain structure to ensure:
        1. First batch of chunks run in parallel (up to max_parallel)
        2. Subsequent batches wait for previous to complete
        3. Final reconciliation runs after all chunks complete
        """
        self.ensure_one()

        pending_chunks = self.chunk_ids.filtered(lambda c: c.state == 'pending')

        if not pending_chunks:
            _logger.warning("No pending chunks to queue for master %s", self.id)
            return

        # Import delay utilities
        from odoo.addons.queue_job.delay import chain, group

        # Create delayables for all chunks
        chunk_delayables = []
        for chunk in pending_chunks.sorted('sequence'):
            delayable = chunk.delayable(
                priority=5,
                max_retries=3,
                description=_('Process reconciliation chunk: %s') % chunk.name,
                channel='root.reconciliation',
            ).action_process()
            chunk_delayables.append(delayable)

        # Group chunks in batches of max_parallel for controlled parallelism
        parallel_groups = []
        for i in range(0, len(chunk_delayables), self.max_parallel_chunks):
            batch = chunk_delayables[i:i + self.max_parallel_chunks]
            if len(batch) > 1:
                parallel_groups.append(group(*batch))
            else:
                parallel_groups.append(batch[0])

        # Create the finalization job
        finalize_delayable = self.delayable(
            priority=10,
            max_retries=2,
            description=_('Finalize reconciliation: %s') % self.name,
            channel='root.reconciliation',
        ).action_finalize()

        # Chain: process all chunk groups, then finalize
        if len(parallel_groups) > 1:
            # Multiple groups: chain them together, then finalize
            job_chain = chain(*parallel_groups)
            job_chain.on_done(finalize_delayable)
            job_chain.delay()
        elif parallel_groups:
            # Single group or single chunk
            parallel_groups[0].on_done(finalize_delayable)
            parallel_groups[0].delay()
        else:
            # No chunks (shouldn't happen)
            finalize_delayable.delay()

        _logger.info("Queued %s chunks for master %s", len(pending_chunks), self.id)

    def action_finalize(self):
        """
        Finalize chunk processing and create move lines.

        This method:
        1. Verifies all chunks completed successfully
        2. Creates all lines in the move (but does NOT reconcile yet)
        3. Stores the reconciliation plan for later execution
        4. Transitions to 'lines_created' state

        Reconciliation is done separately via action_reconcile_batch or
        action_queue_reconciliation to avoid timeouts.
        """
        self.ensure_one()

        _logger.info("Finalizing master reconciliation %s (creating lines only)", self.id)

        # Check for failed chunks
        failed_chunks = self.chunk_ids.filtered(lambda c: c.state == 'failed')
        if failed_chunks:
            error_msg = _('Cannot finalize: %s chunks failed. Please retry or cancel.') % len(failed_chunks)
            self.write({
                'state': 'failed',
                'error_message': error_msg,
                'end_time': fields.Datetime.now(),
            })
            self._notify_failure(error_msg)
            return

        # Check all chunks are done
        pending_chunks = self.chunk_ids.filtered(lambda c: c.state not in ('done', 'cancelled'))
        if pending_chunks:
            _logger.warning("Master %s has %s pending chunks, deferring finalization",
                          self.id, len(pending_chunks))
            return

        try:
            # Create move lines (without reconciliation)
            self._create_move_lines()

            # Calculate totals
            total_lines = sum(self.chunk_ids.mapped('created_line_count'))

            self.write({
                'state': 'lines_created',
                'created_move_line_count': total_lines,
            })

            self._notify_lines_created()

            _logger.info(
                "Master %s: lines created. %s lines ready, %s pairs pending reconciliation",
                self.id, total_lines, self.total_pairs_to_reconcile
            )

        except Exception as e:
            _logger.error("Failed to finalize master %s: %s", self.id, e, exc_info=True)
            self.write({
                'state': 'failed',
                'error_message': str(e),
                'end_time': fields.Datetime.now(),
            })
            self._notify_failure(str(e))
            raise

    def _create_move_lines(self):
        """
        Create all lines in the move (WITHOUT reconciliation).

        The chunks have prepared the line data but NOT written to the move.
        This method:
        1. Collects all prepared line data from chunks
        2. Creates all lines in the move at once (ensuring balance)
        3. Stores the reconciliation plan for later execution

        Reconciliation is handled separately by action_reconcile_batch
        or action_queue_reconciliation.
        """
        self.ensure_one()

        st_line = self.st_line_id
        move = st_line.move_id

        if not move:
            raise UserError(_('Statement line has no associated move.'))

        # Get liquidity account
        journal = st_line.journal_id
        liquidity_account = journal.default_account_id

        # Get the liquidity line (this is the statement line amount)
        liquidity_line = move.line_ids.filtered(
            lambda l: l.account_id == liquidity_account
        )[:1]

        if not liquidity_line:
            raise UserError(_('Could not find liquidity line in statement move.'))

        # Collect all prepared line data from chunks
        all_prepared_data = []
        for chunk in self.chunk_ids.filtered(lambda c: c.state == 'done'):
            try:
                prepared_data = json.loads(chunk.prepared_lines_json or '[]')
                all_prepared_data.extend(prepared_data)
            except (json.JSONDecodeError, TypeError):
                _logger.warning("Invalid prepared lines data in chunk %s", chunk.id)

        if not all_prepared_data:
            _logger.info("No lines to create for master %s", self.id)
            return

        _logger.info("Creating %s lines for master %s", len(all_prepared_data), self.id)

        # Calculate the target balance (inverse of liquidity line)
        target_balance = -liquidity_line.balance
        target_amount_currency = -liquidity_line.amount_currency
        company_currency = self.company_id.currency_id

        # Calculate total of prepared lines
        total_prepared_balance = sum(
            item['line_vals'].get('balance', 0.0) for item in all_prepared_data
        )
        total_prepared_amount_currency = sum(
            item['line_vals'].get('amount_currency', 0.0) for item in all_prepared_data
        )

        # Calculate difference that needs auto-balance line
        balance_diff = target_balance - total_prepared_balance
        amount_currency_diff = target_amount_currency - total_prepared_amount_currency

        _logger.info(
            "Master %s: target_balance=%.2f, total_prepared=%.2f, diff=%.2f",
            self.id, target_balance, total_prepared_balance, balance_diff
        )

        # Build line commands
        line_commands = []

        # First, delete existing non-liquidity lines
        lines_to_delete = move.line_ids.filtered(
            lambda l: l.account_id != liquidity_account
        )
        for line in lines_to_delete:
            line_commands.append(Command.delete(line.id))

        current_sequence = max(move.line_ids.mapped('sequence') or [0]) + 1

        # Store mapping from sequence to counterpart_ids for reconciliation
        reconciliation_plan = []

        # Create lines exactly as prepared (DO NOT adjust - amounts must match counterparts)
        for item in all_prepared_data:
            line_vals = item['line_vals']
            counterpart_ids = item.get('counterpart_ids', [])

            balance = line_vals.get('balance', 0.0)
            amount_currency = line_vals.get('amount_currency', 0.0)

            # Prepare the line with proper debit/credit
            final_line_vals = {
                'sequence': current_sequence,
                'name': line_vals.get('name', ''),
                'partner_id': line_vals.get('partner_id'),
                'account_id': line_vals.get('account_id'),
                'currency_id': line_vals.get('currency_id'),
                'amount_currency': amount_currency,
                'balance': balance,
                'debit': balance if balance > 0 else 0.0,
                'credit': -balance if balance < 0 else 0.0,
            }

            line_commands.append(Command.create(final_line_vals))

            # Store reconciliation data
            if counterpart_ids:
                reconciliation_plan.append({
                    'sequence': current_sequence,
                    'counterpart_ids': counterpart_ids,
                })

            current_sequence += 1

        # If there's a difference, create an auto-balance line
        if not company_currency.is_zero(balance_diff):
            _logger.info(
                "Master %s: Creating auto-balance line for difference: %.2f",
                self.id, balance_diff
            )

            auto_balance_account = self.auto_balance_account_id or journal.suspense_account_id

            if not auto_balance_account:
                raise UserError(_(
                    'Cannot create auto-balance line: no suspense account configured for journal %s'
                ) % journal.display_name)

            auto_balance_vals = {
                'sequence': current_sequence,
                'name': _('Auto-balance (Batch Reconciliation)'),
                'account_id': auto_balance_account.id,
                'currency_id': st_line.currency_id.id or company_currency.id,
                'amount_currency': amount_currency_diff,
                'balance': balance_diff,
                'debit': balance_diff if balance_diff > 0 else 0.0,
                'credit': -balance_diff if balance_diff < 0 else 0.0,
            }

            line_commands.append(Command.create(auto_balance_vals))
            _logger.info("Auto-balance line: %s", auto_balance_vals)

        # Write all lines at once
        _logger.info("Writing %s line commands to move %s", len(line_commands), move.id)

        move_ctx = move.with_context(
            force_delete=True,
            skip_readonly_check=True,
            tracking_disable=True,
            check_move_validity=False,
        )

        move_ctx.write({'line_ids': line_commands})

        # Store move reference and reconciliation plan for later
        self.write({
            'reconciliation_move_id': move.id,
            'reconciliation_plan_json': json.dumps(reconciliation_plan),
            'total_pairs_to_reconcile': len(reconciliation_plan),
            'reconciled_pairs_count': 0,
            'last_reconciled_index': 0,
        })

        # Update partner bank if needed
        if st_line.account_number and st_line.partner_id:
            partner_bank = st_line._find_or_create_bank_account()
            if partner_bank:
                st_line.with_context(
                    skip_account_move_synchronization=True,
                    skip_readonly_check=True
                ).partner_bank_id = partner_bank

        _logger.info(
            "Master %s: Created %s lines, %s pairs pending reconciliation",
            self.id, len(line_commands), len(reconciliation_plan)
        )

    # =========================================================================
    # Reconciliation Actions (Manual and Queued)
    # =========================================================================

    def action_reconcile_batch(self):
        """
        Reconcile the next batch of pairs manually.

        This is called by the user clicking the "Reconcile Batch" button.
        Processes reconciliation_batch_size pairs and updates progress.

        Returns an action to refresh the view with updated progress.
        """
        self.ensure_one()

        if self.state not in ('lines_created', 'reconciling'):
            raise UserError(_('Can only reconcile when lines are created.'))

        if self.reconciled_pairs_count >= self.total_pairs_to_reconcile:
            # Already done
            return self._complete_reconciliation()

        # Start reconciliation phase if not already
        if self.state == 'lines_created':
            self.write({
                'state': 'reconciling',
                'reconciliation_start_time': fields.Datetime.now(),
            })

        # Process one batch
        reconciled_count = self._reconcile_next_batch()

        if self.reconciled_pairs_count >= self.total_pairs_to_reconcile:
            return self._complete_reconciliation()

        # Return action to refresh and show progress
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reconciliation Progress'),
                'message': _('Reconciled %(done)s/%(total)s pairs (%(percent).1f%%)') % {
                    'done': self.reconciled_pairs_count,
                    'total': self.total_pairs_to_reconcile,
                    'percent': self.reconciliation_progress,
                },
                'type': 'info',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'batch.reconciliation.master',
                    'res_id': self.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                }
            }
        }

    def action_queue_reconciliation(self):
        """
        Queue the entire reconciliation process to run in background.

        Uses queue_job to process reconciliation in batches without
        blocking the user interface.
        """
        self.ensure_one()

        if self.state not in ('lines_created', 'reconciling'):
            raise UserError(_('Can only queue reconciliation when lines are created.'))

        if self.auto_reconcile_queued:
            raise UserError(_('Reconciliation is already queued.'))

        if self.reconciled_pairs_count >= self.total_pairs_to_reconcile:
            return self._complete_reconciliation()

        # Mark as queued and start if needed
        vals = {'auto_reconcile_queued': True}
        if self.state == 'lines_created':
            vals.update({
                'state': 'reconciling',
                'reconciliation_start_time': fields.Datetime.now(),
            })
        self.write(vals)

        # Queue the reconciliation job
        self.delayable(
            priority=5,
            max_retries=3,
            description=_('Background reconciliation: %s') % self.name,
            channel='root.reconciliation',
        )._process_queued_reconciliation().delay()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reconciliation Queued'),
                'message': _('Reconciliation of %(total)s pairs has been queued. '
                           'You will be notified when complete.') % {
                    'total': self.total_pairs_to_reconcile - self.reconciled_pairs_count,
                },
                'type': 'info',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'batch.reconciliation.master',
                    'res_id': self.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                }
            }
        }

    def _job_store_values_for__process_queued_reconciliation(self, job):
        return {'is_enqueue_if_started': True}

    def _process_queued_reconciliation(self):
        """
        Process reconciliation in background via queue_job.

        Processes all remaining pairs in batches, committing after each batch.
        """
        self.ensure_one()

        _logger.info("Starting queued reconciliation for master %s", self.id)

        try:
            while self.reconciled_pairs_count < self.total_pairs_to_reconcile:
                # Process one batch
                self._reconcile_next_batch()

                # Commit after each batch to save progress
                self.env.cr.commit()

                _logger.info(
                    "Master %s: Queued reconciliation progress %s/%s",
                    self.id, self.reconciled_pairs_count, self.total_pairs_to_reconcile
                )

            # Complete
            self._complete_reconciliation()

        except Exception as e:
            _logger.error(
                "Queued reconciliation failed for master %s at pair %s: %s",
                self.id, self.last_reconciled_index, e, exc_info=True
            )
            self.write({
                'error_message': str(e),
                'auto_reconcile_queued': False,
            })
            raise

    def check_complete_reconciled(self):
        for rec in self.search([('state', '=', 'reconciling')]):
            if rec.reconciled_pairs_count >= rec.total_pairs_to_reconcile:
                rec._complete_reconciliation()

    def _reconcile_next_batch(self):
        """
        Reconcile the next batch of pairs.

        Returns the number of pairs reconciled in this batch.
        """
        self.ensure_one()

        # Load reconciliation plan
        try:
            reconciliation_plan = json.loads(self.reconciliation_plan_json or '[]')
        except (json.JSONDecodeError, TypeError):
            _logger.error("Invalid reconciliation plan for master %s", self.id)
            return 0

        if not reconciliation_plan:
            return 0

        # Get the move and build sequence mapping
        move = self.reconciliation_move_id
        if not move:
            raise UserError(_('Reconciliation move not found.'))

        sequence2line = {l.sequence: l for l in move.line_ids}

        # Determine batch range
        start_idx = self.last_reconciled_index
        end_idx = min(start_idx + self.reconciliation_batch_size, len(reconciliation_plan))

        if start_idx >= len(reconciliation_plan):
            return 0

        # Build lines to reconcile for this batch
        lines_to_reconcile = []
        for i in range(start_idx, end_idx):
            rec_item = reconciliation_plan[i]
            created_line = sequence2line.get(rec_item['sequence'])
            counterpart_lines = self.env['account.move.line'].browse(
                rec_item['counterpart_ids']
            ).exists()

            if created_line and counterpart_lines:
                lines_to_reconcile.append(created_line + counterpart_lines)

        # Perform reconciliation
        if lines_to_reconcile:
            _logger.info(
                "Master %s: Reconciling batch %s-%s (%s pairs)",
                self.id, start_idx, end_idx, len(lines_to_reconcile)
            )

            self.env['account.move.line'].with_context(
                no_exchange_difference_no_recursive=True
            )._reconcile_plan(lines_to_reconcile)

        # Update progress
        reconciled_count = end_idx - start_idx
        self.write({
            'last_reconciled_index': end_idx,
            'reconciled_pairs_count': self.reconciled_pairs_count + reconciled_count,
        })

        return reconciled_count

    def _complete_reconciliation(self):
        """
        Mark reconciliation as complete and transition to final state.
        """
        self.ensure_one()

        self.write({
            'state': 'reconciled',
            'reconciliation_end_time': fields.Datetime.now(),
            'end_time': fields.Datetime.now(),
            'reconciled_aml_count': self.reconciled_pairs_count,
            'auto_reconcile_queued': False,
        })

        self._notify_completion()

        _logger.info(
            "Master %s: Reconciliation complete. %s pairs reconciled.",
            self.id, self.reconciled_pairs_count
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reconciliation Complete'),
                'message': _('Successfully reconciled %(count)s pairs.') % {
                    'count': self.reconciled_pairs_count,
                },
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'batch.reconciliation.master',
                    'res_id': self.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                }
            }
        }

    def action_view_reconciliation_move(self):
        """Navigate to the reconciliation move."""
        self.ensure_one()
        if not self.reconciliation_move_id:
            raise UserError(_('No reconciliation move created yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reconciliation Move'),
            'res_model': 'account.move',
            'res_id': self.reconciliation_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # =========================================================================
    # User Actions
    # =========================================================================

    def action_cancel(self):
        """Cancel the reconciliation job."""
        self.ensure_one()

        if self.state in ('done', 'reconciled', 'cancelled'):
            raise UserError(_('Cannot cancel a completed or already cancelled job.'))

        # Cancel all pending chunks
        pending_chunks = self.chunk_ids.filtered(
            lambda c: c.state in ('pending', 'processing')
        )
        pending_chunks.write({'state': 'cancelled'})

        self.write({
            'state': 'cancelled',
            'end_time': fields.Datetime.now(),
            'auto_reconcile_queued': False,
        })

        return True

    def action_retry_failed(self):
        """Retry all failed chunks."""
        self.ensure_one()

        if self.state not in ('failed', 'processing'):
            raise UserError(_('Can only retry failed or processing jobs.'))

        failed_chunks = self.chunk_ids.filtered(lambda c: c.state == 'failed')

        if not failed_chunks:
            raise UserError(_('No failed chunks to retry.'))

        # Reset failed chunks
        failed_chunks.write({
            'state': 'pending',
            'error_message': False,
            'retry_count': 0,
        })

        # Re-queue
        self.write({
            'state': 'processing',
            'error_message': False,
            'auto_reconcile_queued': False,
        })

        self._queue_chunks()

        return self._get_notification_action(
            _('Retry Started'),
            _('Retrying %s failed chunks.') % len(failed_chunks),
            'info'
        )

    def action_resume_reconciliation(self):
        """Resume reconciliation after a failure or interruption."""
        self.ensure_one()

        if self.state != 'failed':
            raise UserError(_('Can only resume failed jobs.'))

        # Check if we're in the reconciliation phase (lines already created)
        if self.reconciliation_move_id and self.reconciliation_plan_json:
            # Resume from where we left off
            self.write({
                'state': 'reconciling' if self.reconciled_pairs_count > 0 else 'lines_created',
                'error_message': False,
                'auto_reconcile_queued': False,
            })

            return self._get_notification_action(
                _('Reconciliation Resumed'),
                _('You can continue reconciliation from pair %(current)s/%(total)s.') % {
                    'current': self.last_reconciled_index,
                    'total': self.total_pairs_to_reconcile,
                },
                'info'
            )
        else:
            raise UserError(_('No reconciliation in progress. Use "Retry Failed Chunks" instead.'))

    def action_view_chunks(self):
        """Open chunks view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Processing Chunks'),
            'res_model': 'batch.reconciliation.chunk',
            'view_mode': 'list,form',
            'domain': [('master_id', '=', self.id)],
            'context': {'default_master_id': self.id},
        }

    def action_view_statement_line(self):
        """Navigate to the bank statement line."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bank Statement Line'),
            'res_model': 'account.bank.statement.line',
            'res_id': self.st_line_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_queue_jobs(self):
        """View related queue jobs."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Queue Jobs'),
            'res_model': 'queue.job',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.queue_job_ids.ids)],
        }

    # =========================================================================
    # Notifications
    # =========================================================================

    def _notify_lines_created(self):
        """Send notification when move lines are created (pending reconciliation)."""
        self.ensure_one()

        message = _(
            'Move lines created successfully. Ready for reconciliation.\n\n'
            'Batches: %(batches)s\n'
            'Total Payments: %(total)s\n'
            'Chunks Processed: %(chunks)s\n'
            'Created Lines: %(lines)s\n'
            'Pairs to Reconcile: %(pairs)s\n\n'
            'Click "Reconcile Batch" to process manually or '
            '"Queue Reconciliation" for background processing.'
        ) % {
            'batches': self.batch_payment_names,
            'total': self.total_payments,
            'chunks': self.total_chunks,
            'lines': self.created_move_line_count,
            'pairs': self.total_pairs_to_reconcile,
        }

        self.message_post(
            body=message,
            subject=_('Lines Created - Ready for Reconciliation'),
            message_type='notification',
        )

    def _notify_completion(self):
        """Send notification when master completes successfully."""
        self.ensure_one()

        # Calculate reconciliation duration if available
        recon_duration = 0.0
        if self.reconciliation_start_time and self.reconciliation_end_time:
            delta = self.reconciliation_end_time - self.reconciliation_start_time
            recon_duration = delta.total_seconds()

        message = _(
            'Batch reconciliation completed successfully.\n\n'
            'Batches: %(batches)s\n'
            'Total Payments: %(total)s\n'
            'Chunks Processed: %(chunks)s\n'
            'Total Duration: %(duration).2f seconds\n'
            'Reconciliation Duration: %(recon_duration).2f seconds\n'
            'Created Lines: %(lines)s\n'
            'Reconciled Pairs: %(recons)s'
        ) % {
            'batches': self.batch_payment_names,
            'total': self.total_payments,
            'chunks': self.total_chunks,
            'duration': self.duration,
            'recon_duration': recon_duration,
            'lines': self.created_move_line_count,
            'recons': self.reconciled_aml_count,
        }

        self.message_post(
            body=message,
            subject=_('Reconciliation Completed'),
            message_type='notification',
        )

    def _notify_failure(self, error_msg):
        """Send notification when master fails."""
        self.ensure_one()

        message = _(
            'Batch reconciliation FAILED.\n\n'
            'Error: %(error)s\n\n'
            'Completed Chunks: %(completed)s/%(total)s\n'
            'Failed Chunks: %(failed)s\n\n'
            'Please review and retry or cancel.'
        ) % {
            'error': error_msg,
            'completed': self.completed_chunks,
            'total': self.total_chunks,
            'failed': self.failed_chunks,
        }

        self.message_post(
            body=message,
            subject=_('Reconciliation Failed'),
            message_type='notification',
        )

    def _get_notification_action(self, title, message, msg_type='info'):
        """Return notification action for UI."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': msg_type,
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'batch.reconciliation.master',
                    'res_id': self.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                }
            }
        }
