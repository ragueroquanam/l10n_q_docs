# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartnerAccount(models.Model):
    _name = 'res.partner.account'
    _description = 'Cuentas para los asientos'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    partner_id = fields.Many2one('res.partner')
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True)
    account_receivable_id = fields.Many2one('account.account',
        string="Cuenta a cobrar",
        check_company=True,
        domain="[('account_type', 'in', ('asset_receivable', 'liability_credit_card')), ('deprecated', '=', False), '|', ('currency_id', '=', currency_id), ('currency_id', '=', False)]")
    account_payable_id = fields.Many2one('account.account',
        string="Cuenta a pagar",
        check_company=True,
        domain="[('account_type', 'in', ('liability_payable', 'liability_credit_card')), ('deprecated', '=', False), '|', ('currency_id', '=', currency_id), ('currency_id', '=', False)]")

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        domain=lambda self: [('id', 'in', self.env.companies.ids)]
    )

    _sql_constraints = [
        ('unique_partner_account_currency', 'unique(partner_id, currency_id, company_id)',
         'Asientos Contables por Moneda - Ya existe un registro con la misma moneda y compañia.')
    ]

    @api.onchange('currency_id')
    def _onchange_currency_id_reset_accounts(self):
        self.account_receivable_id = False
        self.account_payable_id = False
