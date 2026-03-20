# -*- coding: utf-8 -*-

import re
from odoo import models, fields, _
from datetime import date

import unicodedata

EXPECTED_LENGTHS_CREDITOS_DIRECTOS = {
    'd1': 5,  # Código de empresa asignado
    'd2': 9,  # Cédula de identidad del titular (sin dígito verificador)
    'd3': 2,  # Mes del cargo
    'd4': 4,  # Año del cargo
    'd5': 1,  # Moneda (P=Pesos / U=Dólares)
    'd6': 12,  # Importe a debitar (últimos 2 = decimales)
    'd7': 2,  # Integrantes del grupo
    'd8': 8,  # Número de factura
    'd9': 12,  # Importe Neto
    'd10': 1,  # Si devuelve IVA (S/N)
    'd11': 11,  # Importe IVA devuelto
}

COLUMNS_TITLES_CREDITOS_DIRECTOS = {
    'd1': 'Código de empresa asignado',
    'd2': 'Cédula de identidad del titular',
    'd3': 'Mes del cargo',
    'd4': 'Año del cargo',
    'd5': 'Moneda',
    'd6': 'Importe a debitar',
    'd7': 'Integrantes del grupo',
    'd8': 'Número de factura',
    'd9': 'Importe Neto',
    'd10': 'Devuelve IVA',
    'd11': 'Importe IVA devuelto',
}


class AccountBatchPaymentFileConfig(models.Model):
    _inherit = "account.bank.payment.file.config"

    def check_payments_for_errors(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """
        rslt = super(AccountBatchPaymentFileConfig, self).check_payments_for_errors(payments)
        if self.code == 'creditos_directos':
            dcredits_rslt = []

            # Variables requeridas: 1 (Código de empresa asignado),5 (Moneda), 7 (Integrantes del grupo), 10 (Devuelve IVA)
            config_h_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [1, 5, 7, 10] if k not in config_h_vars]
            for k in missing_keys:
                dcredits_rslt.append({
                    'title': _("La variable %s no está configurada en el encabezado del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

            values = self._get_values_direct_credits(payments)
            dcredits_rslt.extend(values.get('dcredits_rslt', []))
            rslt.extend(dcredits_rslt)
        return rslt

    def _generate_payment_file_direct_credits(self, payments):
        return self._get_values_direct_credits(payments).get('file', '')

    def _get_values_direct_credits(self, payments):
        file = ""
        config_vars = {line.sequence: line for line in self.line_ids}
        dcredits_rslt = []

        for payment in payments:
            invoice_ids = getattr(payment, 'invoice_ids', None)
            invoice = invoice_ids[0] if invoice_ids else None

            # Código de empresa asignado
            if config_vars.get(1) and config_vars.get(1).type == 'mapping':
                d1 = self._get_mapped_value(
                    config_vars.get(1, False),
                    payment.company_id.vat,
                    COLUMNS_TITLES_CREDITOS_DIRECTOS['d1'],
                    payment,
                    dcredits_rslt
                )
            else:
                d1 = config_vars.get(1).value if config_vars.get(1) else ''

            # Cédula de identidad del titular (sin dígito verificador)
            d2 = self.get_ci_without_verifier(payment.partner_id.vat)

            # Mes del cargo
            d3 = payment.date.strftime('%m')

            # Año del cargo
            d4 = payment.date.strftime('%Y')

            # Moneda (P=Pesos / U=Dólares)
            d5 = self._get_mapped_value(
                config_vars.get(5),
                payment.currency_id.name,
                COLUMNS_TITLES_CREDITOS_DIRECTOS['d5'],
                payment,
                dcredits_rslt
            )

            # Importe a debitar (últimos 2 = decimales)
            d6 = f"{payment.amount:.2f}".replace('.', '')

            # Integrantes del grupo
            d7 = config_vars.get(7).value if config_vars.get(7) else ''

            # Número de factura
            if invoice:
                invoice_number_str = invoice.name or ''
                d8 = self.get_invoice_direct_credits(invoice_number_str)
            else:
                d8 = ' '

            # Importe Neto
            d9 = sum(invoice_ids.mapped('taxable_amount')) if invoice_ids else 0.0
            d9 = str(d9).replace('.', '')

            # Devuelve IVA
            if config_vars.get(10) and config_vars.get(10).type == 'mapping':
                aplica = getattr(payment, 'vat_refund_applicable', None)
                aplica_odoo = 'true' if aplica else 'false' if aplica is not None else ''
                d10 = self._get_mapped_value(
                    config_vars.get(10) if config_vars.get(10) else '',
                    aplica_odoo,
                    COLUMNS_TITLES_CREDITOS_DIRECTOS['d10'],
                    payment,
                    dcredits_rslt
                )
            else:
                d10 = config_vars.get(10).value if config_vars.get(10) else ''

            # Importe IVA devuelto
            d11 = 0.0
            d11 = str(d11).replace('.', '')

            # Setear los valores con el padding y largo esperado
            d1 = self._format_field_direct_credits(d1, 'd1', '0')
            d2 = self._format_field_direct_credits(d2, 'd2', '0')
            d3 = self._format_field_direct_credits(d3, 'd3', '0')
            d4 = self._format_field_direct_credits(d4, 'd4', '0')
            d5 = self._format_field_direct_credits(d5, 'd5', ' ')
            d6 = self._format_field_direct_credits(d6, 'd6', '0')
            d7 = self._format_field_direct_credits(d7, 'd7', '0')
            d8 = self._format_field_direct_credits(d8, 'd8', '0')
            d9 = self._format_field_direct_credits(d9, 'd9', '0')
            d10 = self._format_field_direct_credits(d10, 'd10', ' ')
            d11 = self._format_field_direct_credits(d11, 'd11', '0')

            c_list = [d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11]

            separator = self.column_separator or ''
            file += separator.join(c_list) + '\n'
        return {'file': file, 'dcredits_rslt': dcredits_rslt}

    def _format_field_direct_credits(self, value, field_name, padding=''):
        length = EXPECTED_LENGTHS_CREDITOS_DIRECTOS[field_name]
        return str(value)[:length].rjust(length, padding)

    def get_invoice_direct_credits(self, invoice_number_str):
        # Tomar solo la última parte del string (luego del último espacio)
        clean_str = invoice_number_str.strip().split()[-1]

        # Extraer letras (serie) y números
        match = re.match(r'^([A-Za-z]{1,2})?(\d+)$', clean_str)
        if not match:
            return re.sub(r'\D', '', clean_str)

        # serie = match.group(1).upper() if match and match.group(1) else ''
        number = match.group(2) if match and match.group(2) else ''

        return number

    def get_ci_without_verifier(self, ci_raw):
        if not ci_raw:
            return ''

        # Eliminar lo que no sea número
        ci_clean = re.sub(r'\D', '', ci_raw)

        if len(ci_clean) <= 1:
            return ''

        # Quitar el último dígito (dígito verificador)
        return ci_clean[:-1] if len(ci_clean) > 7 else ci_clean
