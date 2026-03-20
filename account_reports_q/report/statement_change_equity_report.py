# -*- coding: utf-8 -*-

from datetime import datetime

import pytz
from odoo import api, models, fields

COLUMN_TYPES = {
    'capital': 'Capital',
    'comp': 'Aportes y Comprom. a Capital',
    'adjust': 'Ajustes al patrimonio',
    'reserve': 'Reservas',
    'result': 'Resultados acumulados',
}

SECTIONS_TYPES = {
    1: 'Saldos iniciales',
    2: u'Modificación al saldo inicial',
    3: 'Movimientos del ejercicio',
    4: 'Saldo finales'
}


def patrimonial_evolution(self, data):
    date_from = data['form']['date_from']
    date_to = data['form']['date_to']
    target_move = data['form']['new_target_move']
    fiscalyear = data['form']['fiscalyear_id']
    company = self.env.user.company_id.name
    StatementChangesEquityConf = self.env['statement.changes.equity.conf']
    AccountMoveLine = self.env['account.move.line']
    docargs = {
        'sections': {},
        'fiscalyear': fiscalyear,
        'company': company,
        'target_move': target_move,
    }

    # Por cada Sección
    for key in SECTIONS_TYPES.keys():
        # Crear una lista para la seccion
        docargs['sections'][key] = []

        # Buscar las evoluciones patrimoniales correspondientes a la seccion que sean del tipo cuenta y tengan un
        # padre
        for evolution in StatementChangesEquityConf.search([('section', '=', key), ('type', '=', 'accounts')]):
            evolution_name = evolution.name
            # Buscar en la lista de secciones si ya se guardo un rubro igual al de esta evolución
            match = list(filter(lambda x: x['name'] == evolution_name, docargs['sections'][key]))

            # Si se encontro
            if match:
                # Trabajar con el rubro guardado
                rubro = match[0]
            else:
                # del lo contrario crear un nuevo record para el rubro y adicionarlo a la lista de secciones
                rubro = {
                    'name': evolution_name,
                    'capital': float(0),
                    'comp': float(0),
                    'adjust': float(0),
                    'reserve': float(0),
                    'result': float(0),
                }
                docargs['sections'][key].append(rubro)

            # Por cada tipos de columnas
            for column in COLUMN_TYPES.keys():
                # Filtrar las cuentas por cada tipos de columnas
                line_ids = evolution.line_ids.filtered(lambda x: x.headers == column)

                for line in line_ids:
                    if line.amount_option == 'initial_balance':
                        rubro[column] += account_initial_balance(AccountMoveLine, date_from, line.account_id.id,
                                                                 target_move)
                    elif line.amount_option == 'balance':
                        rubro[column] += account_balance(AccountMoveLine, date_from, date_to, line.account_id.id,
                                                         target_move)
                    else:
                        rubro[column] += account_close_balance(AccountMoveLine, date_to, line.account_id.id,
                                                               target_move)

                if rubro[column] != 0:
                    # Invertir o mantener el signo según el valor del campo "Sign en informes"
                    rubro[column] *= int(evolution.sign)

    return docargs


def account_initial_balance(AccountMoveLine, date_from, account_id, target_move):
    """ Saldo que tiene la cuenta contable en el período 0 del año seleccionado en la emisión del reporte. """

    domain = [("account_id", "=", account_id), ("date", "<", date_from)]

    if target_move == "posted":
        domain.append(('move_id.state', '=', target_move))

    return sum(AccountMoveLine.search(domain).mapped(lambda n: n.debit - n.credit))


def account_balance(AccountMoveLine, date_from, date_to, account_id, target_move):
    """  Movimientos contables (neto entre debe/haber de la cuenta involucrada) del ejercicio seleccionado en la
    emisión del reporte """

    domain = [("account_id", "=", account_id),
              ("date", ">=", date_from), ("date", "<=", date_to)]

    if target_move == "posted":
        domain.append(('move_id.state', '=', target_move))

    return sum(AccountMoveLine.search(domain).mapped(lambda n: n.debit - n.credit))


def account_close_balance(AccountMoveLine, date_to, account_id, target_move):
    """ Muestra la suma de los dos anteriores  (los movimientos del período y los movimientos para el período 0,
    que es el de apertura). """

    domain = [("account_id", "=", account_id), ("date", "<=", date_to)]

    if target_move == "posted":
        domain.append(('move_id.state', '=', target_move))

    return sum(AccountMoveLine.search(domain).mapped(lambda n: n.debit - n.credit))


# Reporte PDF de Evolución Patrimonaial
class ReportEvolucionPatrimonio(models.AbstractModel):
    _name = 'report.account_reports_q.report_statement_changes_equity'
    _description = 'report.account_reports_q.report_statement_changes_equity'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name(
            'account_reports_q.report_statement_changes_equity')
        selected_modules = self.env['statement.changes.equity.wizard'].browse(docids)
        docargs = patrimonial_evolution(self, data)
        docargs.update({
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': selected_modules
        })
        return docargs


class ReportEvolucionPatrimonioXlsx(models.AbstractModel):
    _name = 'report.account_reports_q.statement_changes_equity_xlsx'
    _description = 'report.account_reports_q.statement_changes_equity_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def define_formats(self, workbook):
        return {
            "heading_format": workbook.add_format({
                "align": "left", "valign": "vcenter", "bold": True, "font_size": 16
            }),
            "sub_heading_format": workbook.add_format({
                "align": "left", "valign": "vcenter", "font_size": 12
            }),
            "cell_header_format": workbook.add_format({
                "align": "center", "valign": "vcenter", 'text_wrap': True,
                "font_size": 12, "bold": True, "border": True
            }),
            "cell_text_format": workbook.add_format({
                "align": "left", "valign": "vcenter", "font_size": 12, "border": True
            }),
            "cell_bold_text_format": workbook.add_format({
                "bold": True, "align": "left", "valign": "vcenter",
                "font_size": 12, "border": True
            }),
            "cell_number_format": workbook.add_format({
                "align": "right", "valign": "vcenter", "font_size": 12, "border": True,
                "num_format": '#,##0.00'
            }),
            "cell_bold_number_format": workbook.add_format({
                "bold": True, "align": "right", "valign": "vcenter",
                "font_size": 12, "border": True, "num_format": '#,##0.00'
            }),
        }

    def generate_xlsx_report(self, workbook, data, obj):
        docargs = patrimonial_evolution(self, data)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)

        TOTALS = ['TOTAL SALDOS INICIALES', 'SALDOS INIC. MODIFICADOS', 'SUB TOTAL', 'TOTAL SALDOS FINALES']

        formats = self.define_formats(workbook)
        heading_format = formats["heading_format"]
        sub_heading_format = formats["sub_heading_format"]
        cell_header_format = formats["cell_header_format"]
        cell_text_format = formats["cell_text_format"]
        cell_bold_text_format = formats["cell_bold_text_format"]
        cell_number_format = formats["cell_number_format"]
        cell_bold_number_format = formats["cell_bold_number_format"]

        worksheet = workbook.add_worksheet(str(fields.Date.today()))

        worksheet.merge_range("A1:F2", u"ESTADO DE EVOLUCIÓN DEL PATRIMONIO", heading_format)
        worksheet.merge_range("A4:D4", u"DENOMINACIÓN DE LA EMPRESA:", sub_heading_format)
        worksheet.merge_range("E4:H4", docargs["company"], sub_heading_format)
        worksheet.merge_range("N4:O4", u"EJERCICIO", sub_heading_format)
        worksheet.merge_range("N5:O5", u"FECHA DE EMISIÓN", sub_heading_format)
        worksheet.merge_range("N6:O6", u"HORA DE EMISIÓN", sub_heading_format)
        worksheet.merge_range("P4:Q4", "%s" % docargs["fiscalyear"], sub_heading_format)
        worksheet.merge_range("P5:Q5", "%s" % ((datetime.today()).strftime('%d/%m/%Y')), sub_heading_format)
        worksheet.merge_range("P6:Q6", "%s" % (
            pytz.utc.localize(datetime.now(), is_dst=False).astimezone(local).strftime("%H:%M")), sub_heading_format)
        target_move_str = u"MOVIMIENTOS PUBLICADOS" if docargs["target_move"] == "posted" else u"TODOS LOS MOVIMIENTOS"
        worksheet.merge_range("A5:D5", target_move_str, sub_heading_format)

        worksheet.merge_range("A8:E9", u"CONCEPTO", cell_header_format)
        worksheet.merge_range("F8:G9", u"CAPITAL", cell_header_format)
        worksheet.merge_range("H8:I9", u"APORTES Y COMPROM. A CAPITALIZ.", cell_header_format)
        worksheet.merge_range("J8:K9", u"AJUSTES AL PATRIMON.", cell_header_format)
        worksheet.merge_range("M8:L9", u"RESERVAS", cell_header_format)
        worksheet.merge_range("N8:O9", u"RESULT. ACUMUL.", cell_header_format)
        worksheet.merge_range("P8:Q9", u"PATRIMONIO TOTAL", cell_header_format)

        row_pos = 9

        for key, value in SECTIONS_TYPES.items():
            row_pos += 1
            # Imprimir el nombre de la seccion
            worksheet.merge_range("A%d:E%d" % (row_pos, row_pos), value.upper(), cell_bold_text_format)
            worksheet.merge_range("F%d:G%d" % (row_pos, row_pos), "", cell_text_format)
            worksheet.merge_range("H%d:I%d" % (row_pos, row_pos), "", cell_text_format)
            worksheet.merge_range("J%d:K%d" % (row_pos, row_pos), "", cell_text_format)
            worksheet.merge_range("M%d:L%d" % (row_pos, row_pos), "", cell_text_format)
            worksheet.merge_range("N%d:O%d" % (row_pos, row_pos), "", cell_text_format)
            worksheet.merge_range("P%d:Q%d" % (row_pos, row_pos), "", cell_text_format)

            start_range = row_pos + 1
            end_range = start_range + len(docargs['sections'][key]) - 1
            is_multi_col = end_range > start_range

            for rubro in docargs['sections'][key]:
                row_pos += 1
                row_sum = sum([v for k, v in rubro.items() if k != "name"])

                worksheet.merge_range("A%d:E%d" % (row_pos, row_pos), "  " * 4 + "%s" % rubro["name"],
                                      cell_text_format)
                worksheet.merge_range("F%d:G%d" % (row_pos, row_pos), rubro["capital"],
                                      cell_number_format)
                worksheet.merge_range("H%d:I%d" % (row_pos, row_pos), rubro["comp"], cell_number_format)
                worksheet.merge_range("J%d:K%d" % (row_pos, row_pos), rubro["adjust"],
                                      cell_number_format)
                worksheet.merge_range("L%d:M%d" % (row_pos, row_pos), rubro["reserve"],
                                      cell_number_format)
                worksheet.merge_range("N%d:O%d" % (row_pos, row_pos), rubro["result"],
                                      cell_number_format)
                worksheet.merge_range("P%d:Q%d" % (row_pos, row_pos), row_sum, cell_number_format)

            row_pos += 1
            worksheet.merge_range("A%d:E%d" % (row_pos, row_pos), TOTALS[key - 1], cell_text_format)
            worksheet.merge_range(
                "F%d:G%d" % (row_pos, row_pos),
                "=SUM(F%d:G%d)" % (start_range, end_range) if is_multi_col else "=SUM(F%d)" % start_range,
                cell_bold_number_format)
            worksheet.merge_range(
                "H%d:I%d" % (row_pos, row_pos),
                "=SUM(H%d:I%d)" % (start_range, end_range) if is_multi_col else "=SUM(H%d)" % start_range,
                cell_bold_number_format)
            worksheet.merge_range(
                "J%d:K%d" % (row_pos, row_pos),
                "=SUM(J%d:K%d)" % (start_range, end_range) if is_multi_col else "=SUM(J%d)" % start_range,
                cell_bold_number_format)
            worksheet.merge_range(
                "L%d:M%d" % (row_pos, row_pos),
                "=SUM(L%d:M%d)" % (start_range, end_range) if is_multi_col else "=SUM(L%d)" % start_range,
                cell_bold_number_format)
            worksheet.merge_range(
                "N%d:O%d" % (row_pos, row_pos),
                "=SUM(N%d:O%d)" % (start_range, end_range) if is_multi_col else "=SUM(N%d)" % start_range,
                cell_bold_number_format)
            worksheet.merge_range(
                "P%d:Q%d" % (row_pos, row_pos),
                "=SUM(P%d:Q%d)" % (start_range, end_range) if is_multi_col else "=SUM(P%d)" % start_range,
                cell_bold_number_format)

        for i in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q"]:
            worksheet.set_column("%s:%s" % (i, i), 10)
