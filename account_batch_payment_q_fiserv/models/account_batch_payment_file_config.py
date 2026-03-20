# -*- coding: utf-8 -*-

import re
from odoo import models, fields, _
from datetime import date

import unicodedata

# Expected lengths for HEADER and DETAIL fields according to specification
EXPECTED_LENGTHS_FISERV_HEADER = {
    'h1': 8,  # Numero comercio
    'h2': 1,  # Tipo registro
    'h3': 6,  # Fecha presentacion DDMMAA
    'h4': 7,  # Cantidad de registros (up to 7)
    'h5': 1,  # Signo importe
    'h6': 14,  # Importe (12,2) -> 12 int + 2 decimals = 14
    'h7': 1,  # Moneda
    'h8': 162,  # Filler
}

EXPECTED_LENGTHS_FISERV_DETAIL = {
    'd1': 8,  # Numero comercio
    'd2': 1,  # Tipo de registro(2)
    'd3': 16,  # Numero de tarjeta
    'd4': 12,  # Nro de Referencia (right aligned, zeros)
    'd5': 3,  # Cuotas (001)
    'd6': 3,  # Cuotas/Plan
    'd7': 2,  # Frecuencia DB (01)
    'd8': 11,  # Importe (9,2) -> 9+2 = 11
    'd9': 5,  # Periodo
    'd10': 1,  # Filler
    'd11': 6,  # Fecha VTO (DDMMAA) or blanks
    'd12': 40,  # Datos auxiliares
    'd13': 1,  # Marca aplica devol IVA (0/1)
    'd14': 11,  # Importe Gravado (9,2) -> 11
    'd15': 20,  # Nro Factura
    'd16': 60,  # Filler
}

COLUMNS_TITLES_FISERV_HEADER = {
    'h1': 'Numero Comercio',
    'h2': 'Numero Registro',
    'h3': 'Fecha Presentacion',
    'h4': 'Cantidad Registros',
    'h5': 'Signo Importe',
    'h6': 'Importe Total',
    'h7': 'Moneda',
    'h8': 'Filler',
}

COLUMNS_TITLES_FISERV_DETAIL = {
    'd1': 'Numero Comercio',
    'd2': 'Tipo Registro',
    'd3': 'Numero Tarjeta',
    'd4': 'Nro Referencia',
    'd5': 'Cuotas',
    'd6': 'Cuotas/Plan',
    'd7': 'Frecuencia DB',
    'd8': 'Importe',
    'd9': 'Periodo',
    'd10': 'Filler',
    'd11': 'Fecha Vto Pago',
    'd12': 'Datos Auxiliares',
    'd13': 'Marca Aplica Devol IVA',
    'd14': 'Importe Gravado',
    'd15': 'Nro Factura',
    'd16': 'Filler',
}


class AccountBatchPaymentFileConfig(models.Model):
    _inherit = "account.bank.payment.file.config"

    def check_payments_for_errors(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """
        rslt = super(AccountBatchPaymentFileConfig, self).check_payments_for_errors(payments)
        if self.code == 'fiserv':
            fiserv_rslt = []

            # required variables header: 1 (comercio),2 (registro),7 (moneda)
            config_h_vars = {line.sequence: line for line in self.header_ids}
            missing_keys = [k for k in [1, 2, 7] if k not in config_h_vars]
            for k in missing_keys:
                fiserv_rslt.append({
                    'title': _("La variable %s no está configurada en el encabezado del archivo de pago FISERV.") % k,
                    'records': payments,
                    'help': ''
                })

            # required variables: 1 (comercio),2 (registro), 5 (cuotas fijo),7 (frecuencia),13 (map aplica devol iva)
            config_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [1, 2, 5, 7, 13] if k not in config_vars]
            for k in missing_keys:
                fiserv_rslt.append({
                    'title': _("La configuración de archivo de pago FISERV no tiene la variable %s configurada.") % k,
                    'records': payments,
                    'help': ''
                })

            # Call value generator to collect line-specific errors
            values = self._get_values_fiserv(payments)
            fiserv_rslt.extend(values.get('fiserv_rslt', []))
            rslt.extend(fiserv_rslt)
        return rslt

    def _generate_payment_file(self, payments):
        """
        Genera una plantilla de pago a partir de los pagos proporcionados.

        :param payments: Lista de pagos a procesar.
        :return: Plantilla de pago generada.
        """
        if self.code == 'fiserv':
            return self._generate_payment_file_fiserv(payments)
        return super(AccountBatchPaymentFileConfig, self)._generate_payment_file(payments)

    def _generate_payment_file_fiserv(self, payments):
        return self._get_values_fiserv(payments).get('file', '')

    def _get_values_fiserv(self, payments):
        """
        Build FISERV file: single HEADER line + many DETAIL lines (one per payment)
        Uses configuration variables stored in self.line_ids (sequence numbers as per spec)
        """
        file_lines = ''
        config_h_vars = {line.sequence: line for line in self.header_ids}
        fiserv_rslt = []

        # Calculated aggregates
        total_records = len(payments)
        total_amount = sum(payment.amount for payment in payments) or 0.0
        total_amount_signed = sum(payment.amount_signed for payment in payments) or 0.0

        # HEADER fields
        h1 = self._get_mapped_value(
            config_h_vars.get(1, False),
            payments[0].company_id.vat,
            COLUMNS_TITLES_FISERV_HEADER['h1'],
            payments[0],
            fiserv_rslt
        )
        h1 = h1.rjust(EXPECTED_LENGTHS_FISERV_HEADER['h1'], '0')

        h2 = (config_h_vars.get(2) and config_h_vars.get(2).value) or ''
        # h3 date
        batch_date = payments[0].batch_payment_id.date if payments and payments[0].batch_payment_id else None
        # fallback to today's date formatting if not found
        if batch_date:
            h3 = fields.Date.to_string(batch_date)[8:10] + fields.Date.to_string(batch_date)[
                5:7] + fields.Date.to_string(batch_date)[2:4]
        else:
            today = date.today()
            h3 = today.strftime('%d%m%y')

        # h4 cantidad de registros, right justified zeros, width 7
        h4 = str(total_records).rjust(EXPECTED_LENGTHS_FISERV_HEADER['h4'], '0')

        # h5 signo importe
        h5 = '0' if total_amount_signed >= 0 else '-'

        # h6 importe total: remove decimal point, ensure 2 decimals, then pad left zeros to length 14
        h6 = f"{abs(total_amount):.2f}".replace('.', '')
        h6 = h6.rjust(EXPECTED_LENGTHS_FISERV_HEADER['h6'], '0')

        # h7 moneda mapping via variable 7 (mapping)
        h7 = self._get_mapped_value(
            config_h_vars.get(7, False),
            payments[0].currency_id.name if payments else '',
            COLUMNS_TITLES_FISERV_HEADER['h7'],
            payments[0],
            fiserv_rslt
        )
        h7 = h7.ljust(EXPECTED_LENGTHS_FISERV_HEADER['h7'], ' ')

        h8 = ''.ljust(EXPECTED_LENGTHS_FISERV_HEADER['h8'], ' ')

        # Build header line and check lengths
        header_list = [h1, h2, h3, h4, h5, h6, h7, h8]
        # pad/trim header pieces to expected widths
        header_list = [
            str(v)[:EXPECTED_LENGTHS_FISERV_HEADER[f'h{idx + 1}']].ljust(
                EXPECTED_LENGTHS_FISERV_HEADER[f'h{idx + 1}'], ' '
            )
            for idx, v in enumerate(header_list)
        ]

        fiserv_rslt.extend(self._check_header_lengths(header_list, payments))
        separator = self.column_separator or ''
        file_lines += separator.join(header_list) + '\n'

        # DETAIL lines
        # prefetch some config variables used in detail
        config_vars = {line.sequence: line for line in self.line_ids}
        type_rec = config_vars.get(2) and (config_vars.get(2).value) or ''  # Tipo registro detalle (should be '2')
        d5_fix = config_vars.get(5) and (config_vars.get(5).value) or '001'  # Cuotas fijo
        d7_fix = config_vars.get(7) and (config_vars.get(7).value) or '01'  # Frecuencia DB
        d13_line = config_vars.get(13, False)  # mapping for aplica devol iva

        for payment in payments:
            # D1 Número de comercio
            d1 = self._get_mapped_value(
                config_vars.get(1, False),
                payments.company_id.vat,
                COLUMNS_TITLES_FISERV_DETAIL['d1'],
                payment,
                fiserv_rslt
            )
            d1 = d1.rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d1'], '0')

            # d2 tipo registro
            d2 = type_rec or ''
            # d3 numero tarjeta
            d3 = self._get_card_number_for_payment(payment) or ''
            if not d3.strip():
                fiserv_rslt.append({
                    'title': _("El pago %s no tiene número de tarjeta configurado en el afiliado.") % payment.name,
                    'records': payment,
                    'help': ''
                })

            # d4 nro referencia -> use payment.reference or payment.communication or id; right aligned zeros width 12
            raw_ref = payment.name if hasattr(payment, 'name') else ''
            if '/' in raw_ref:
                ref = raw_ref.split('/')[-1]
            else:
                ref = ''.join(c for c in raw_ref if c.isdigit())
            d4 = str(ref)[-EXPECTED_LENGTHS_FISERV_DETAIL['d4']:]  # trim rightmost
            d4 = d4.rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d4'], '0')

            # d5 cuotas fijo
            d5 = str(d5_fix).rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d5'], '0')
            # d6 cuotas/plan: try payment.installments_count or plan field else '000'
            d6 = str(getattr(payment, 'installments_count', '') or '999').rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d6'],
                                                                                '0')
            if d6.strip('0') == '':
                d6 = ''.rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d6'], '0')

            # d7 frecuencia
            d7 = str(d7_fix).rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d7'], '0')

            # d8 importe (per payment) -> format abs, remove dot, pad left zeros width 11
            amt = getattr(payment, 'amount', 0.0) or 0.0
            d8 = f"{abs(amt):.2f}".replace('.', '').rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d8'], '0')

            # d9 periodo (formato "1YYMM", por ejemplo: "12301" para enero de 2023)
            if payment.date:
                year = payment.date.strftime('%y')  # último dígito del año, ej: '23'
                month = payment.date.strftime('%m')  # mes con dos dígitos, ej: '01'
                period = f"1{year}{month}"
            else:
                period = ''
            d9 = str(period)[:EXPECTED_LENGTHS_FISERV_DETAIL['d9']].ljust(EXPECTED_LENGTHS_FISERV_DETAIL['d9'], ' ')

            d10 = ' '
            # d11 fecha vto pago
            invoice_ids = getattr(payment, 'invoice_ids', None)
            if invoice_ids:
                due_dates = [d for d in invoice_ids.mapped("invoice_date_due") if d]
                due = min(due_dates) if due_dates else False
                d11 = fields.Date.to_string(due)[8:10] + fields.Date.to_string(due)[5:7] + fields.Date.to_string(due)[
                    2:4]
            else:
                d11 = ''.rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d11'], ' ')

            d12 = ''.ljust(EXPECTED_LENGTHS_FISERV_DETAIL['d12'], ' ')

            # d13 marca aplica devol iva -> mapping via variable 21
            aplica = getattr(payment, 'vat_refund_applicable', None)
            aplica_odoo = 'true' if aplica else 'false' if aplica is not None else ''
            d13 = self._get_mapped_value(
                config_vars.get(13, False),
                aplica_odoo,
                COLUMNS_TITLES_FISERV_DETAIL['d13'],
                payment,
                fiserv_rslt
            )
            d13 = d13.rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d13'], '0')

            # d14 importe gravado
            conv_gravado = 0.0
            if invoice_ids:
                conv_gravado = sum(invoice_ids.mapped('taxable_amount')) or 0.0
            d14 = f"{abs(conv_gravado):.2f}".replace('.', '').rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d14'], '0')

            # d15 nro factura -> invoice.name
            invoice = invoice_ids[0] if invoice_ids else None
            serie, number = self.get_invoice_oca(invoice.name if invoice else '')
            number_len = EXPECTED_LENGTHS_FISERV_DETAIL['d15'] - len(serie)
            number = self._format_field_oca(number, number_len, numeric_fill='0', align='right')
            d15 = f"{serie}{number}"
            d15 = str(d15)[:EXPECTED_LENGTHS_FISERV_DETAIL['d15']].rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d15'], ' ')

            d16 = ''.ljust(EXPECTED_LENGTHS_FISERV_DETAIL['d16'], ' ')

            detail_list = [d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11, d12, d13, d14, d15, d16]

            # Ensure each piece matches expected length (pad/trim)
            norm_detail = []
            for idx, val in enumerate(detail_list, start=1):
                key = f'd{idx}'
                exp = EXPECTED_LENGTHS_FISERV_DETAIL.get(key)
                s = str(val) if val is not None else ''
                s = s[:exp].ljust(exp, ' ')
                norm_detail.append(s)

            fiserv_rslt.extend(self._check_detail_lengths(payment, norm_detail))
            separator = self.column_separator or ''
            file_lines += separator.join(norm_detail) + '\n'

        return {'file': file_lines, 'fiserv_rslt': fiserv_rslt}

    def _check_header_lengths(self, header_list, payments):
        rslt = []
        for i, value in enumerate(header_list, start=1):
            key = f'h{i}'
            expected = EXPECTED_LENGTHS_FISERV_HEADER.get(key)
            if expected is None:
                continue
            actual_len = len(value)
            if actual_len != expected:
                rslt.append({
                    'title': _('El campo %s con valor %s no tiene la longitud correcta. Se espera %s') % (
                        COLUMNS_TITLES_FISERV_HEADER.get(key, key), value, expected
                    ),
                    'records': payments,
                    'help': ''
                })
        return rslt

    def _check_detail_lengths(self, payment, detail_list):
        rslt = []
        for i, value in enumerate(detail_list, start=1):
            key = f'd{i}'
            expected = EXPECTED_LENGTHS_FISERV_DETAIL.get(key)
            if expected is None:
                continue
            actual_len = len(value)
            if actual_len != expected:
                rslt.append({
                    'title': _('El campo %s con valor %s no tiene la longitud correcta. Se espera %s') % (
                        COLUMNS_TITLES_FISERV_DETAIL.get(key, key), value, expected
                    ),
                    'records': payment,
                    'help': ''
                })
        return rslt

    def _get_card_number_for_payment(self, payment):
        card_info_dict = self._get_card_info(payment)
        card = card_info_dict.get('card_number', '')
        if card:
            cleaned = ''.join(ch for ch in str(card) if ch.isdigit())
            return cleaned[:EXPECTED_LENGTHS_FISERV_DETAIL['d3']].rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d3'], '0')
        return ''.rjust(EXPECTED_LENGTHS_FISERV_DETAIL['d3'], ' ')

    def sanitize_str(self, value, length=50):
        if not value:
            return ' ' * length
        # Replace Ñ/ñ with # per your previous rule
        value = value.replace('Ñ', '#').replace('ñ', '#')
        # ü -> u, Ü -> U
        value = value.replace('ü', 'u').replace('Ü', 'U')
        normalized = unicodedata.normalize('NFKD', value)
        ascii_str = ''.join(c for c in normalized if not unicodedata.combining(c))
        ascii_str = ascii_str[:length].ljust(length, ' ')
        return ascii_str

    def get_invoice_fiserv(self, invoice_number_str):
        clean_str = invoice_number_str.strip().split()[-1]

        match = re.match(r'^([A-Za-z]{1,2})?(\d+)$', clean_str)
        if not match:
            return re.sub(r'\D', '', clean_str)

        serie = match.group(1).upper() if match and match.group(1) else ''
        number = match.group(2) if match and match.group(2) else ''

        return serie, number