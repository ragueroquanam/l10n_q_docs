# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Create optimized indexes for batch reconciliation after module install."""
    _logger.info("Creating optimized indexes for batch reconciliation...")

    cr = env.cr

    # Index for account.move.line searches by move_id and display_type
    # Used in bulk prefetch of invoice term lines
    cr.execute("""
        CREATE INDEX IF NOT EXISTS account_move_line_move_display_type_idx
        ON account_move_line (move_id, display_type)
        WHERE display_type = 'payment_term';
    """)

    # Index for payment searches by state and batch_payment_id
    cr.execute("""
        CREATE INDEX IF NOT EXISTS account_payment_batch_state_idx
        ON account_payment (batch_payment_id, state)
        WHERE batch_payment_id IS NOT NULL;
    """)

    # Index for reconciliation lookups
    cr.execute("""
        CREATE INDEX IF NOT EXISTS account_move_line_account_reconciled_idx
        ON account_move_line (account_id, reconciled, company_id)
        WHERE reconciled = false;
    """)

    # Index for statement line move lookups
    cr.execute("""
        CREATE INDEX IF NOT EXISTS account_bank_statement_line_move_idx
        ON account_bank_statement_line (move_id)
        WHERE move_id IS NOT NULL;
    """)

    # Index for queue_job state lookups (if not exists from queue_job module)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS queue_job_model_state_idx
        ON queue_job (model_name, state)
        WHERE state IN ('pending', 'enqueued', 'started');
    """)

    _logger.info("Optimized indexes created successfully")
