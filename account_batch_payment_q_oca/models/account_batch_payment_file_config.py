# -*- coding: utf-8 -*-

import re
from odoo import models, fields, _


EXPECTED_LENGTHS_OCA = {
    # según tu spec, ajustado si fuese necesario
    'd1': 12, 'd2': 3, 'd3': 9, 'd4': 7, 'd5': 1,
    'd6': 20, 'd7': 9, 'd8': 9,
}

EXPECTED_LENGTHS_PADRON = {
    'p1': 12, 'p2': 1, 'p3': 1, 'p4': 1, 'p5': 1,
    'p6': 1, 'p7': 1, 'p8': 18, 'p9': 7
}

COLUMNS_TITLES_OCA = {
    'd1': 'Nro de Socio de la Institución',
    'd2': 'Código Moneda',
    'd3': 'Importe',
    'd4': 'Cédula del Tarjetahabiente',
    'd5': 'Aplica Devolución IVA',
    'd6': 'Número de Factura',
    'd7': 'Importe Gravado sin IVA',
    'd8': 'Importe Retenido',
}

COLUMNS_TITLES_PATRONES_OCA = {
    'p1': 'Convenio-Matrícula',
    'p2': 'Nombre del Socio',
    'p3': 'Apellido del Socio',
    'p4': 'Dirección',
    'p5': 'Teléfono',
    'p6': 'Celular',
    'p7': 'Cédula del Socio',
    'p8': 'Número de Tarjeta',
    'p9': 'Cédula del Tarjetahabiente',
}


class AccountBatchPaymentFileConfig(models.Model):
    _inherit = "account.bank.payment.file.config"

    def check_payments_for_errors(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """
        rslt = super(AccountBatchPaymentFileConfig, self).check_payments_for_errors(payments)
        _rslt = []
        if self.code == 'oca':
            # required variables: 2 (moneda),5 (map aplica devol iva)
            config_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [2, 5] if k not in config_vars]
            for k in missing_keys:
                _rslt.append({
                    'title': _("La configuración de archivo de pago OCA no tiene la variable %s configurada.") % k,
                    'records': payments,
                    'help': ''
                })

            rslt.extend(_rslt)
            rslt.extend(self._get_values_oca(payments).get('_rslt', []))
        elif self.code == 'oca_padrones':
            # required variables
            config_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [2, 3, 4, 5, 6, 7] if k not in config_vars]
            for k in missing_keys:
                _rslt.append({
                    'title': _(
                        "La configuración de archivo de pago OCA padrones no tiene la variable %s configurada.") % k,
                    'records': payments,
                    'help': ''
                })

            rslt.extend(_rslt)
            rslt.extend(self._get_values_oca_padrones(payments).get('_rslt', []))

        return rslt

    def _generate_payment_file_oca(self, payments):
        """
        Genera una plantilla de pago a partir de los pagos proporcionados para ITAU.

        :param payments: Lista de pagos a procesar.
        :return: Texto para fichero de pago.
        """
        return self._get_values_oca(payments).get('file', '')

    def _generate_payment_file_oca_padrones(self, payments):
        """
        Genera una plantilla de pago a partir de los pagos proporcionados para ITAU.

        :param payments: Lista de pagos a procesar.
        :return: Texto para fichero de pago.
        """
        return self._get_values_oca_padrones(payments).get('file', '')

    def _format_field_oca(self, value, length=None, numeric_fill=' ', align='left'):
        """Sanitize and pad/trim to length."""
        s = '' if value is None else str(value)
        s = ''.join(ch for ch in s if ord(ch) >= 32)  # eliminar control chars
        if length:
            if align == 'left':
                return s[:length].ljust(length, ' ')
            else:
                return s[-length:].rjust(length, numeric_fill)
        return s

    def _get_values_oca(self, payments):
        file = ""
        config_vars = {line.sequence: line for line in self.line_ids}
        _rslt = []
        for pay in payments:
            invoice = pay.invoice_ids and pay.invoice_ids[0] or None
            if not invoice:
                _rslt.append({
                    'title': _("El pago %s no tiene factura asociada.") % pay.name,
                    'records': pay,
                    'help': ''
                })

            # 1. Nro socio institución: convenio + matrícula
            convenio = invoice.agreement_id.code if invoice and hasattr(invoice, 'agreement_id') else ''
            matricula = invoice.commercial_registration if invoice and hasattr(invoice, 'commercial_registration') else ''
            matricula = self._format_field_oca(matricula, 7, numeric_fill=' ', align='right')
            if convenio and matricula:
                d1 = f"{convenio}{matricula}"
            else:
                d1 = convenio or matricula or pay.partner_id.ref or ''
            d1 = self._format_field_oca(d1, EXPECTED_LENGTHS_OCA['d1'], numeric_fill=' ', align='right')

            # 2. Moneda
            d2 = self._get_mapped_value(
                config_vars.get(2, False),
                pay.currency_id.name,
                COLUMNS_TITLES_OCA['d2'],
                payments[0],
                _rslt
            )
            d2 = d2.ljust(EXPECTED_LENGTHS_OCA['d2'], ' ')

            # 3. Importe (amount_signed)
            amt = pay.amount_signed or 0.0
            d3 = f"{amt:.2f}".replace('.', '').rjust(EXPECTED_LENGTHS_OCA['d3'], ' ')

            # 4. Cédula del tarjetahabiente
            card_info_dict = self._get_card_info(pay)
            card_holder_id = card_info_dict.get('card_holder_id', '')
            if card_holder_id:
                partner = self.env['res.partner'].browse(card_holder_id)
                card_partner = partner.vat if partner else ''
            else:
                card_partner = invoice.partner_id.vat if invoice else ''
            d4 = self._format_field_oca(card_partner, EXPECTED_LENGTHS_OCA['d4'], align='right', numeric_fill='0')

            # 5. Aplica devolución IVA: True=1, False=0
            aplica = getattr(pay, 'vat_refund_applicable', None)
            aplica_odoo = 'true' if aplica else 'false' if aplica is not None else ''
            d5 = self._get_mapped_value(
                config_vars.get(13, False),
                aplica_odoo,
                COLUMNS_TITLES_OCA['d5'],
                pay,
                _rslt
            )
            d5 = d5.rjust(EXPECTED_LENGTHS_OCA['d5'], '0')

            # 6. Número de factura
            serie, number = self.get_invoice_oca(invoice.name if invoice else '')
            number = self._format_field_oca(number, 17, numeric_fill='0', align='right')
            d6 = f"{serie}{number}"
            d6 = str(d6)[:EXPECTED_LENGTHS_OCA['d6']].rjust(EXPECTED_LENGTHS_OCA['d6'], ' ')

            # 7. Importe gravado sin IVA
            gravado = invoice.taxable_amount if invoice and hasattr(invoice, 'taxable_amount') else 0.0
            d7 = f"{gravado:.2f}".replace('.', '').rjust(EXPECTED_LENGTHS_OCA['d7'], '0')

            # 8. Importe retenido
            reten = 0
            d8 = f"{reten:.2f}".replace('.', '').rjust(EXPECTED_LENGTHS_OCA['d8'], '0')

            c_list = [
                d1, d2, d3, d4, d5, d6, d7, d8
            ]
            separator = self.column_separator or ''
            file += separator.join(c_list) + '\n'

        return {'file': file, '_rslt': _rslt}

    def _get_values_oca_padrones(self, payments):
        file = ""
        _rslt = []
        config_vars = {line.sequence: line for line in self.line_ids}
        for pay in payments:
            invoice = pay.invoice_ids and pay.invoice_ids[0] or None
            if not invoice:
                _rslt.append({
                    'title': _("El pago %s no tiene factura asociada.") % pay.name,
                    'records': pay,
                    'help': ''
                })

            # 1. Convenio-Matrícula
            convenio = invoice.agreement_id.code if invoice and hasattr(invoice, 'agreement_id') else ''
            matricula = invoice.commercial_registration if invoice and hasattr(invoice, 'commercial_registration') else ''
            matricula = self._format_field_oca(matricula, 7, numeric_fill=' ', align='right')
            if convenio and matricula:
                p1 = f"{convenio}{matricula}"
            else:
                p1 = convenio or matricula or pay.partner_id.ref or ''
            p1 = self._format_field_oca(p1, EXPECTED_LENGTHS_PADRON['p1'], numeric_fill=' ', align='right')

            # 2-4. Nombre, Apellido, Dirección
            p2 = config_vars.get(2) and (config_vars.get(2).value) or '*'
            p2 = str(p2)[:EXPECTED_LENGTHS_PADRON['p2']].rjust(EXPECTED_LENGTHS_PADRON['p2'], ' ')
            p3 = config_vars.get(3) and (config_vars.get(3).value) or '*'
            p3 = str(p3)[:EXPECTED_LENGTHS_PADRON['p3']].rjust(EXPECTED_LENGTHS_PADRON['p3'], ' ')
            p4 = config_vars.get(4) and (config_vars.get(4).value) or '*'
            p4 = str(p4)[:EXPECTED_LENGTHS_PADRON['p4']].rjust(EXPECTED_LENGTHS_PADRON['p4'], ' ')

            # 5. Teléfono; 6. Celular
            p5 = config_vars.get(5) and (config_vars.get(5).value) or '*'
            p5 = str(p5)[:EXPECTED_LENGTHS_PADRON['p5']].rjust(EXPECTED_LENGTHS_PADRON['p5'], ' ')
            p6 = config_vars.get(6) and (config_vars.get(6).value) or '*'
            p6 = str(p6)[:EXPECTED_LENGTHS_PADRON['p6']].rjust(EXPECTED_LENGTHS_PADRON['p6'], ' ')

            # 7. Cédula del socio
            p7 = config_vars.get(7) and (config_vars.get(7).value) or '5'
            p7 = self._format_field_oca(p7, EXPECTED_LENGTHS_PADRON['p7'], numeric_fill=' ', align='right')

            # 8. Número de tarjeta
            card_info_dict = self._get_card_info(pay)
            num_tarj = card_info_dict.get('card_number', '')
            num_tarj = '' if not num_tarj else num_tarj.strip()
            if not num_tarj:
                _rslt.append({
                    'title': _("El pago %s no tiene número de tarjeta configurado en el afiliado.") % pay.name,
                    'records': pay,
                    'help': ''
                })

            p8 = self._format_field_oca(num_tarj, EXPECTED_LENGTHS_PADRON['p8'], numeric_fill=' ', align='right')

            # 9. Cédula tarjetahabiente (mismo campo del pago)
            card_holder_id = card_info_dict.get('card_holder_id', '')
            if card_holder_id:
                partner = self.env['res.partner'].browse(card_holder_id)
                card_partner = partner.vat if partner else ''
            else:
                card_partner = invoice.partner_id.vat if invoice else ''
            p9 = self._format_field_oca(card_partner, EXPECTED_LENGTHS_PADRON['p9'], align='right', numeric_fill='0')

            c_list = [
                p1, p2, p3, p4, p5, p6, p7, p8, p9
            ]
            separator = self.column_separator or ''
            file += separator.join(c_list) + '\n'

        return {'file': file, '_rslt': _rslt}

    def get_invoice_oca(self, invoice_number_str):
        clean_parts = (invoice_number_str or '').strip().split()
        if not clean_parts:
            return '', ''
        clean_str = clean_parts[-1]

        # Extraer letras (serie) y números
        match = re.match(r'^([A-Za-z]{1,2})?(\d+)$', clean_str)
        if not match:
            return '', re.sub(r'\D', '', clean_str)

        serie = match.group(1).upper() if match and match.group(1) else ''
        number = match.group(2) if match and match.group(2) else ''

        return serie, number
