from collections import defaultdict

from odoo import fields, models, api


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    partner_account_ids = fields.One2many('res.partner.account', 'partner_id', string='Cuentas Asientos')

    card_number = fields.Char(string='Número de tarjeta')
    card_exp_month = fields.Char(string='Mes de vencimiento', size=2)
    card_exp_year = fields.Char(string='Año de vencimiento', size=2)
    card_holder_id = fields.Many2one('res.partner', string='Tarjetahabiente')

    total_due_currency = fields.Monetary(
        string='Total adeudado en moneda',
        compute='_compute_total_due_currency',
        groups='account.group_account_readonly,account.group_account_invoice',
    )
    total_overdue_currency = fields.Monetary(
        string='Total atrasado en moneda',
        compute='_compute_total_due_currency',
        groups='account.group_account_readonly,account.group_account_invoice',
    )

    def _get_card_info(self):
        """
        Returns the card information associated with the partner.

        Returns a dictionary with the following data:
            - card_exp_month: Card expiration month (str, 2 digits).
            - card_exp_year: Card expiration year (str, 2 digits).
            - card_holder_id: ID of the partner who is the cardholder (int).

        :return: dict with card information.
        """
        self.ensure_one()
        return {
            'card_number': self.card_number,
            'card_exp_month': self.card_exp_month,
            'card_exp_year': self.card_exp_year,
            'card_holder_id': self.card_holder_id.id
        }

    @api.depends('invoice_ids')
    @api.depends_context('company', 'allowed_company_ids', 'due_currency_filter', 'due_currency_company', 'due_currency_foreign')
    def _compute_total_due_currency(self):
        due_data = defaultdict(float)
        overdue_data = defaultdict(float)
        company_currency = self.env.company.currency_id
        ctx = self.env.context
        filter_company = bool(ctx.get('due_currency_company'))
        filter_foreign = bool(ctx.get('due_currency_foreign'))
        currency_filter = ctx.get('due_currency_filter')

        # Backward compatibility for contexts that still send due_currency_filter only.
        if currency_filter in ('company', 'foreign') and not (filter_company or filter_foreign):
            filter_company = currency_filter == 'company'
            filter_foreign = currency_filter == 'foreign'

        # If both (or none) are selected, behave like no filter: use company currency totals.
        if (filter_company and filter_foreign) or (not filter_company and not filter_foreign):
            filter_company = False
            filter_foreign = False

        domain = [
            ('reconciled', '=', False),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('partner_id', 'in', self.ids),
            ('company_id', 'child_of', self.env.company.id),
        ]
        if filter_company:
            domain += [
                '|',
                ('currency_id', '=', False),
                ('currency_id', '=', company_currency.id),
            ]
        elif filter_foreign:
            domain += [
                ('currency_id', '!=', False),
                ('currency_id', '!=', company_currency.id),
            ]

        amount_field = 'amount_residual_currency' if (filter_company or filter_foreign) else 'amount_residual'
        for overdue, partner, amount_sum in self.env['account.move.line']._read_group(
            domain=domain,
            groupby=['followup_overdue', 'partner_id'],
            aggregates=[f'{amount_field}:sum'],
        ):
            due_data[partner] += amount_sum
            if overdue:
                overdue_data[partner] += amount_sum

        for partner in self:
            partner.total_due_currency = due_data.get(partner, 0.0)
            partner.total_overdue_currency = overdue_data.get(partner, 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)

        default_currency = self.env.user.company_id.currency_id

        account_receivable = self.env['ir.default'].sudo()._get(
            'res.partner',
            'property_account_receivable_id',
            company_id=self.env.company.id
        )
        account_payable = self.env['ir.default'].sudo()._get(
            'res.partner',
            'property_account_payable_id',
            company_id=self.env.company.id
        )

        if account_receivable and account_payable:
            partner_accounts = []
            for partner in partners:
                if not partner.partner_account_ids:
                    partner_accounts.append({
                        'partner_id': partner.id,
                        'currency_id': default_currency.id,
                        'account_receivable_id': account_receivable,
                        'account_payable_id': account_payable,
                    })

            if partner_accounts:
                self.env['res.partner.account'].create(partner_accounts)

        return partners

    def write(self, vals):

        result = super(ResPartner, self).write(vals)

        default_currency = self.env.user.company_id.currency_id

        account_receivable = self.env['ir.default'].sudo()._get('res.partner', 'property_account_receivable_id',
                                                                company_id=self.env.company.id)
        account_payable = self.env['ir.default'].sudo()._get('res.partner', 'property_account_payable_id',
                                                             company_id=self.env.company.id)

        for partner in self:
            if not partner.partner_account_ids:

                if account_receivable and account_payable:
                    self.env['res.partner.account'].create({
                        'partner_id': partner.id,
                        'currency_id': default_currency.id,
                        'account_receivable_id': account_receivable,
                        'account_payable_id': account_payable
                    })

        return result
