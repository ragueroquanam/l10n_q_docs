# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields


class StatementChangesEquityWizard(models.TransientModel):
    _name = 'statement.changes.equity.wizard'
    _description = 'Evolucion patrimonio wizard'

    def _get_year_selection(self):
        current_year = date.today().year
        return [(str(y), str(y)) for y in range(current_year, current_year - 11, -1)]

    fiscalyear = fields.Selection(
        selection=_get_year_selection,
        string='Año Fiscal',
        required=True,
        default=lambda self: str(date.today().year)
    )
    new_target_move = fields.Selection([('posted', 'Publicados'),
                                        ('all', 'Todos'),
                                        ], string='Movimientos', required=True, default='posted')

    def check_report(self):
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(['fiscalyear', 'new_target_move'])[0]
        }
        fiscalyear = self.fiscalyear
        year = int(fiscalyear)
        company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date(year, 1, 1))
        date_from = company_fiscalyear_dates['date_from']
        date_to = company_fiscalyear_dates['date_to']
        data['form'].update({
            'date_from': date_from,
            'date_to': date_to,
            'fiscalyear_id': year,
            'new_target_move': self.new_target_move,
        })

        return self.env.ref('account_reports_q.action_report_statement_changes_equity').report_action([],
                                                                                                      data=data)

    def check_report_excel(self):
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(['fiscalyear', 'new_target_move'])[0]
        }
        fiscalyear = self.fiscalyear
        year = int(fiscalyear)
        company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date(year, 1, 1))
        date_from = company_fiscalyear_dates['date_from']
        date_to = company_fiscalyear_dates['date_to']
        data['form'].update({
            'date_from': date_from.strftime('%Y-%m-%d'),
            'date_to': date_to.strftime('%Y-%m-%d'),
            'fiscalyear_id': year,
        })
        return self.env.ref('account_reports_q.action_report_statement_changes_equity_xlsx').report_action([],
                                                                                                           data=data)
