from odoo import models


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    def _compute_account_id(self):
        super()._compute_account_id()

        term_lines = self.filtered(lambda line: line.display_type == 'payment_term')
        if term_lines:
            moves = term_lines.move_id
            self.env.cr.execute("""
                WITH previous AS (
                    SELECT DISTINCT ON (line.move_id)
                           'account.move' AS model,
                           line.move_id AS id,
                           NULL AS account_type,
                           line.account_id AS account_id
                      FROM account_move_line line
                     WHERE line.move_id = ANY(%(move_ids)s)
                       AND line.display_type = 'payment_term'
                       AND line.id != ANY(%(current_ids)s)
                ),
                fallback AS (
                    SELECT DISTINCT ON (account_companies.res_company_id, account.account_type)
                           'res.company' AS model,
                           account_companies.res_company_id AS id,
                           account.account_type AS account_type,
                           account.id AS account_id
                      FROM account_account account
                      JOIN account_account_res_company_rel account_companies
                           ON account_companies.account_account_id = account.id
                     WHERE account_companies.res_company_id = ANY(%(company_ids)s)
                       AND account.account_type IN ('asset_receivable', 'liability_payable')
                       AND account.deprecated = 'f'
                )
                SELECT * FROM previous
                UNION ALL
                SELECT * FROM fallback
            """, {
                'company_ids': moves.company_id.ids,
                'move_ids': moves.ids,
                'partners': [f'res.partner,{pid}' for pid in moves.commercial_partner_id.ids],
                'current_ids': term_lines.ids
            })
            accounts = {
                (model, id, account_type): account_id
                for model, id, account_type, account_id in self.env.cr.fetchall()
            }
            for line in term_lines:
                account_type = 'asset_receivable' if line.move_id.is_sale_document(
                    include_receipts=True) else 'liability_payable'
                move = line.move_id

                partner_account = self.env['res.partner.account'].search([
                    ('partner_id', '=', move.commercial_partner_id.id),
                    ('currency_id', '=', move.currency_id.id),
                    ('company_id', '=', move.company_id.id)], limit=1)

                partner_account_id = None
                if partner_account:
                    partner_account_id = (
                        partner_account.account_receivable_id.id
                        if account_type == 'asset_receivable'
                        else partner_account.account_payable_id.id
                    )

                opt_1 = accounts.get(('account.move', move.id, None))
                opt_2 = partner_account_id
                move_with_company = move.with_company(move.company_id)
                if account_type == 'asset_receivable':
                    opt_3 = move_with_company.commercial_partner_id['property_account_receivable_id'].id
                else:
                    opt_3 = move_with_company.commercial_partner_id['property_account_payable_id'].id
                opt_4 = accounts.get(('res.company', move.company_id.id, account_type))
                account_id = (opt_1 or opt_2 or opt_3 or opt_4)
                if line.move_id.fiscal_position_id:
                    account_id = line.move_id.fiscal_position_id.map_account(
                        self.env['account.account'].browse(account_id))
                line.account_id = account_id
