# -*- coding: utf-8 -*-
import re
from odoo import models, fields, _

EXPECTED_LENGTHS_VISANET1 = {
    'c1': 1,
    'c2': 7,
    'c3': 7,
    'c4': 8,
    'c5': 3,
    'c6': 8,
    'c7': 4,
    'c8': 2,
    'c9': 4,
    'c10': 2,
    'c11': 19,
    'c12': 4,
    'c13': 8,
    'c14': 15,
    'c15': 6,
    'c16': 6,

    'c17': 10,
    'c18': 1,
    'c19': 2,
    'c20': 7,
    'c21': 15,

    'ca': 1,
    'cb': 8,
    'cc': 3,
    'cd': 8,
    'ce': 8,
    'cf': 7,
    'cg': 15,
    'ch': 15,
    'ci': 7,
    'cj': 15,
    'ck': 15,
    'cl': 10,
}

COLUMNS_TITLES_VISANET1 = {
    'c1': 'TIPO DE REGISTRO',
    'c2': 'NRO. DE CABEZAL',
    'c3': 'NRO. DE TRANSACCION',
    'c4': 'NRO. DE COMERCIO',
    'c5': 'NRO. DE SUCURSAL',
    'c6': 'FECHA DE LOTE',
    'c7': 'MONEDA',
    'c8': 'CANTIDAD DE CUOTAS',
    'c9': 'PLAN DE VENTA',
    'c10': 'TIPO DE TRANSACCION',
    'c11': 'NUMERO DE TARJETA',
    'c12': 'VENCIMIENTO DE LA TARJETA',
    'c13': 'FECHA DE TRANSACCION',
    'c14': 'IMPORTE',
    'c15': 'NUMERO DE AUTORIZACION',
    'c16': 'PERIODO',

    'c17': 'SOCIO',
    'c18': 'APLICA DEV IVA',
    'c19': 'SERIE DEL COMPROBANTE',
    'c20': 'NÚMERO DE COMPROBANTE',
    'c21': 'IMPORTE GRAVADO',

    'ca': 'TIPO DE REGISTRO',
    'cb': 'NUMERO DE COMERCIO',
    'cc': 'SUCURSAL DE COMERCIO',
    'cd': 'FECHA DEL ARCHIVO',
    'ce': 'RELATIVO DENTRO DE LA FECHA DEL ARCHIVO',
    'cf': 'TOTAL CANTIDAD DE TRANSACCIONES EN $',
    'cg': 'TOTAL IMPORTE TRANSACCIONES EN $ DE TIPO 05 Y 26',
    'ch': 'TOTAL IMPORTE TRANSACCIONES EN $ DE TIPO 06 Y 25',
    'ci': 'TOTAL CANTIDAD DE TRANSACCIONES EN U$S',
    'cj': 'TOTAL IMPORTE TRANSACCIONES EN U$S DE TIPO 05 Y 26',
    'ck': 'TOTAL IMPORTE TRANSACCIONES EN U$S DE TIPO 06 Y 25',
    'cl': 'AUTOMATIC',
}

EXPECTED_LENGTHS_VISANET2 = {
    'c1': 1,
    'c2': 7,
    'c3': 8,
    'c4': 4,
    'c5': 8,
    'c6': 4,
    'c7': 2,
    'c8': 4,
    'c9': 2,
    'c10': 7,
    'c11': 15,
    'ca': 1,
    'cb': 8,
    'cc': 3,
    'cd': 8,
    'ce': 8,
    'cf': 7,
    'cg': 15,
    'ch': 15,
    'ci': 7,
    'cj': 15,
    'ck': 15,
    'cl': 10,
}

COLUMNS_TITLES_VISANET2 = {
    'c1': 'TIPO DE REGISTRO',
    'c2': 'NRO. DE CABEZAL',
    'c3': 'NRO. DE COMERCIO',
    'c4': 'NRO. DE SUCURSAL',
    'c5': 'FECHA DE LOTE',
    'c6': 'MONEDA',
    'c7': 'CANTIDAD DE CUOTAS',
    'c8': 'PLAN DE VENTA',
    'c9': 'TIPO DE TRANSACCION',
    'c10': 'TOTAL DE TRANSACCIONES DEL CABEZAL',
    'c11': 'TOTAL DE IMPORTE DEL CABEZAL',
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
        if self.code in ("visanet1", "visanet2"):
            # required variables header: 1 (TIPO DE REGISTRO),12 (AUTOMATIC)
            config_f_vars = {line.sequence: line for line in self.footer_ids}
            missing_keys = [k for k in [1, 12] if k not in config_f_vars]
            for k in missing_keys:
                _rslt.append({
                    'title': _("La variable %s no está configurada en la línea de cierre del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

        if self.code == "visanet2":
            config_vars = {line.sequence: line for line in self.line_ids}

            missing_keys = [k for k in [1, 3, 4, 6, 7, 8, 9] if k not in config_vars]
            for k in missing_keys:
                _rslt.append({
                    'title': _("%s: La configuración de archivo de pago no tiene la variable %s configurada.") % (
                        self.name, k),
                    'records': payments,
                    'help': ""
                })
            rslt.extend(_rslt)
            rslt.extend(self._get_values_visanet2(payments).get('_rslt', []))
        elif self.code == "visanet1":

            config_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [1, 4, 5, 7, 8, 9, 10, 18] if k not in config_vars]
            for k in missing_keys:
                _rslt.append({
                    'title': _("%s: La configuración de archivo de pago no tiene la variable %s configurada.") % (
                        self.name, k),
                    'records': payments,
                    'help': ""
                })
            rslt.extend(_rslt)
            rslt.extend(self._get_values_visanet1(payments).get('_rslt', []))
        return rslt

    def _generate_payment_file_visanet2(self, payments):
        """
        Genera una plantilla de pago a partir de los pagos proporcionados para ITAU.

        :param payments: Lista de pagos a procesar.
        :return: Texto para fichero de pago.
        """
        return self._get_values_visanet2(payments).get('file', '')

    def _get_values_visanet2(self, payments):
        file = ""
        config_vars = {line.sequence: line for line in self.line_ids}
        _rslt = []

        line_sequence = 1
        batch_payment = self._context.get('batch_payment')

        for payment in payments:
            line = config_vars.get(1, '')
            c1 = line and line.value or ''
            c2 = str(line_sequence)
            line_sequence += 1

            c3 = self._get_mapped_value(
                config_vars.get(3, False),
                payment.company_id.vat,
                COLUMNS_TITLES_VISANET2['c3'],
                payment,
                _rslt
            )

            c4_line = config_vars.get(4, False)
            c4 = c4_line and c4_line.value or ''

            c5 = batch_payment.date.strftime('%Y%m%d')

            c6 = self._get_mapped_value(
                config_vars.get(6, False),
                payment.currency_id.name,
                COLUMNS_TITLES_VISANET2['c6'],
                payment,
                _rslt
            )

            c7_line = config_vars.get(7, False)
            c7 = c7_line and c7_line.value or ''
            c8_line = config_vars.get(8, False)
            c8 = c8_line and c8_line.value or ''
            c9_line = config_vars.get(9, False)
            c9 = c9_line and c9_line.value or ''

            c10 = str(len(batch_payment.payment_ids))
            c11 = f"{sum(payment.amount_signed for payment in batch_payment.payment_ids):.2f}".replace('.', '')

            # SET FIXED SPACES
            c1 = c1.rjust(EXPECTED_LENGTHS_VISANET2['c1'], '0')
            c2 = c2.rjust(EXPECTED_LENGTHS_VISANET2['c2'], '0')
            c3 = c3.rjust(EXPECTED_LENGTHS_VISANET2['c3'], '0')
            c4 = c4.rjust(EXPECTED_LENGTHS_VISANET2['c4'], '0')
            c5 = c5.rjust(EXPECTED_LENGTHS_VISANET2['c5'], '0')
            c6 = c6.rjust(EXPECTED_LENGTHS_VISANET2['c6'], '0')
            c7 = c7.rjust(EXPECTED_LENGTHS_VISANET2['c7'], '0')
            c8 = c8.rjust(EXPECTED_LENGTHS_VISANET2['c8'], '0')
            c9 = c9.rjust(EXPECTED_LENGTHS_VISANET2['c9'], '0')
            c10 = c10.rjust(EXPECTED_LENGTHS_VISANET2['c10'], '0')
            c11 = c11.rjust(EXPECTED_LENGTHS_VISANET2['c11'], '0')

            c_list = [
                c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11
            ]
            _rslt.extend(self._check_line_lengths_visanet(payment, c_list, EXPECTED_LENGTHS_VISANET2, COLUMNS_TITLES_VISANET2))

            separator = self.column_separator or ''
            file += separator.join(c_list) + '\n'

        config_f_vars = {line.sequence: line for line in self.footer_ids}

        ca = (config_f_vars.get(1) and config_f_vars.get(1).value) or 'T'
        cb = c3
        cc = c4
        cd = fields.Date.today().strftime('%Y%m%d')

        # Realiza un search_count de account.batch.payment para la fecha, diario y método de pago del batch actual
        batch_payments = self.env['account.batch.payment'].sudo().search([
            ('date', '=', batch_payment.date),
            ('journal_id', '=', batch_payment.journal_id.id),
            ('company_id', '=', batch_payment.company_id.id),
            ('payment_method_id', '=', batch_payment.payment_method_id.id),
        ])

        all_attachments = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'account.batch.payment'),
            ('res_id', 'in', batch_payments.ids),
        ])
        ce = str(len(all_attachments))

        uyu_payments = batch_payment.payment_ids.filtered(lambda p: p.currency_id.name == 'UYU')
        cf = str(len(uyu_payments))
        cg = f"{sum(payment.amount_signed for payment in uyu_payments):.2f}".replace('.', '')
        ch = '0'
        usd_payments = batch_payment.payment_ids.filtered(lambda p: p.currency_id.name == 'USD')
        ci = str(len(usd_payments))
        cj = f"{sum(payment.amount_signed for payment in usd_payments):.2f}".replace('.', '')
        ck = '0'
        cl = (config_f_vars.get(12) and config_f_vars.get(12).value) or 'AUTOMATICO'

        # SET FIXED SPACES
        ca = ca.rjust(EXPECTED_LENGTHS_VISANET2['ca'], '0')
        cb = cb.rjust(EXPECTED_LENGTHS_VISANET2['cb'], '0')
        cc = cc.rjust(EXPECTED_LENGTHS_VISANET2['cc'], '0')
        cd = cd.rjust(EXPECTED_LENGTHS_VISANET2['cd'], '0')
        ce = ce.rjust(EXPECTED_LENGTHS_VISANET2['ce'], '0')
        cf = cf.rjust(EXPECTED_LENGTHS_VISANET2['cf'], '0')
        cg = cg.rjust(EXPECTED_LENGTHS_VISANET2['cg'], '0')
        ch = ch.rjust(EXPECTED_LENGTHS_VISANET2['ch'], '0')
        ci = ci.rjust(EXPECTED_LENGTHS_VISANET2['ci'], '0')
        cj = cj.rjust(EXPECTED_LENGTHS_VISANET2['cj'], '0')
        ck = ck.rjust(EXPECTED_LENGTHS_VISANET2['ck'], '0')
        cl = cl.rjust(EXPECTED_LENGTHS_VISANET2['cl'], '0')

        c_list = [
            ca, cb, cc, cd, ce, cf, cg, ch, ci, cj, ck, cl
        ]
        separator = self.column_separator or ''
        file += separator.join(c_list) + '\n'

        return {'file': file, '_rslt': _rslt}

    def _generate_payment_file_visanet1(self, payments):
        """
        Genera una plantilla de pago a partir de los pagos proporcionados para ITAU.

        :param payments: Lista de pagos a procesar.
        :return: Texto para fichero de pago.
        """
        return self._get_values_visanet1(payments).get('file', '')

    def _get_values_visanet1(self, payments):
        file = ""
        config_vars = {}
        _rslt = []
        for line in self.line_ids:
            config_vars[line.sequence] = line

        line_sequence = 1
        batch_payment = self._context.get('batch_payment')

        for payment in payments:
            line = config_vars.get(1, '')
            c1 = line and line.value or ''
            c2 = str(line_sequence)
            line_sequence += 1

            match = re.search(r'(\d+)$', str(payment.name))
            c3 = match.group(1) if match else ''

            c4 = self._get_mapped_value(
                config_vars.get(4, False),
                payment.company_id.vat,
                COLUMNS_TITLES_VISANET1['c4'],
                payment,
                _rslt
            )

            c5_line = config_vars.get(5, False)
            c5 = c5_line and c5_line.value or ''

            c6 = batch_payment.date.strftime('%Y%m%d')

            c7 = self._get_mapped_value(
                config_vars.get(7, False),
                payment.currency_id.name,
                COLUMNS_TITLES_VISANET1['c7'],
                payment,
                _rslt
            )

            c8_line = config_vars.get(8, False)
            c8 = c8_line and c8_line.value or ''
            c9_line = config_vars.get(9, False)
            c9 = c9_line and c9_line.value or ''
            c10_line = config_vars.get(10, False)
            c10 = c10_line and c10_line.value or ''

            partner_card_info = self._get_card_info(payment)

            c11 = partner_card_info.get('card_number', '') or ''
            if not c11:
                _rslt.append({
                    'title': _("El pago %s no tiene número de tarjeta configurado en el afiliado.") % payment.name,
                    'records': payment,
                    'help': ''
                })

            if partner_card_info.get('card_exp_month', '') and partner_card_info.get('card_exp_year', ''):
                c12 = f'{partner_card_info.get("card_exp_month", "")}{partner_card_info.get("card_exp_year", "")}'
            else:
                c12 = '0000'
            c13 = batch_payment.date.strftime('%Y%m%d')
            c14 = f"{payment.amount_signed:.2f}".replace('.', '')
            c15 = '0'

            # Formatea la fecha como ENE/25 (mes abreviado en español/mayúsculas + '/' + dos dígitos de año)
            months = {
                1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR', 5: 'MAY', 6: 'JUN',
                7: 'JUL', 8: 'AGO', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DIC'
            }
            month = months.get(batch_payment.date.month, batch_payment.date.strftime('%b').upper())
            year = batch_payment.date.strftime('%y')
            c16 = f"{month}/{year}"

            source_move_id = payment.invoice_ids[0] if payment.invoice_ids else None
            c17 = self._get_patner_socio(payment) or "0"
            aplica = getattr(payment, 'vat_refund_applicable', None)
            aplica_odoo = 'true' if aplica else 'false' if aplica is not None else ''
            c18 = self._get_mapped_value(
                config_vars.get(18, False),
                aplica_odoo,
                COLUMNS_TITLES_VISANET1['c18'],
                payment,
                _rslt
            )

            # Obtener la serie del comprobante fiscal según la lógica solicitada
            # Ejemplo: "FC A0000065" -> "A ", "FC 1A0000065" -> "1A"
            serie = ''
            if source_move_id and source_move_id.name:
                # Buscar 7 dígitos al final y capturar el carácter anterior
                match = re.search(r'([A-Za-z0-9])(\d{7})$', source_move_id.name.replace(' ', ''))
                if match:
                    serie = match.group(1)
                    # Si la serie es de un solo carácter, agregar un espacio a la derecha
                    if len(serie) == 1:
                        serie = f"{serie} "
                else:
                    # Si no se encuentra el patrón, dejar vacío o poner dos espacios
                    serie = '  '
            else:
                serie = '  '
            c19 = serie

            # Obtener el número del comprobante fiscal: los últimos 7 dígitos del nombre del documento
            c20 = ''
            if source_move_id and source_move_id.name:
                # Eliminar espacios y buscar los últimos 7 dígitos
                match = re.search(r'(\d{7})$', source_move_id.name.replace(' ', ''))
                if match:
                    c20 = match.group(1)
                else:
                    c20 = '0000000'
            else:
                c20 = '0000000'

            c21 = f"{source_move_id.taxable_amount:.2f}".replace('.', '') if source_move_id else '0'

            # SET FIXED SPACES
            c1 = c1.rjust(EXPECTED_LENGTHS_VISANET1['c1'], '0')
            c2 = c2.rjust(EXPECTED_LENGTHS_VISANET1['c2'], '0')
            c3 = c3.rjust(EXPECTED_LENGTHS_VISANET1['c3'], '0')
            c4 = c4.rjust(EXPECTED_LENGTHS_VISANET1['c4'], '0')
            c5 = c5.rjust(EXPECTED_LENGTHS_VISANET1['c5'], '0')
            c6 = c6.rjust(EXPECTED_LENGTHS_VISANET1['c6'], '0')
            c7 = c7.rjust(EXPECTED_LENGTHS_VISANET1['c7'], '0')
            c8 = c8.rjust(EXPECTED_LENGTHS_VISANET1['c8'], '0')
            c9 = c9.rjust(EXPECTED_LENGTHS_VISANET1['c9'], '0')
            c10 = c10.rjust(EXPECTED_LENGTHS_VISANET1['c10'], '0')
            c11 = c11.rjust(EXPECTED_LENGTHS_VISANET1['c11'], '0')
            c12 = c12.rjust(EXPECTED_LENGTHS_VISANET1['c12'], '0')
            c13 = c13.rjust(EXPECTED_LENGTHS_VISANET1['c13'], '0')
            c14 = c14.rjust(EXPECTED_LENGTHS_VISANET1['c14'], '0')
            c15 = c15.rjust(EXPECTED_LENGTHS_VISANET1['c15'], '0')
            c16 = c16.rjust(EXPECTED_LENGTHS_VISANET1['c16'], '0')
            c17 = c17.rjust(EXPECTED_LENGTHS_VISANET1['c17'], '0')
            c18 = c18.rjust(EXPECTED_LENGTHS_VISANET1['c18'], '0')
            c19 = c19.rjust(EXPECTED_LENGTHS_VISANET1['c19'], '0')
            c20 = c20.rjust(EXPECTED_LENGTHS_VISANET1['c20'], '0')
            c21 = c21.rjust(EXPECTED_LENGTHS_VISANET1['c21'], '0')

            c_list = [
                c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c16, c17, c18, c19, c20, c21
            ]
            _rslt.extend(self._check_line_lengths_visanet(payment, c_list, EXPECTED_LENGTHS_VISANET1, COLUMNS_TITLES_VISANET1))

            separator = self.column_separator or ''
            file += separator.join(c_list) + '\n'

        config_f_vars = {line.sequence: line for line in self.footer_ids}

        ca = (config_f_vars.get(1) and config_f_vars.get(1).value) or 'T'
        cb = c4
        cc = c5
        cd = fields.Date.today().strftime('%Y%m%d')
        ce = str(batch_payment.id)

        uyu_payments = batch_payment.payment_ids.filtered(lambda p: p.currency_id.name == 'UYU')
        cf = str(len(uyu_payments))
        cg = f"{sum(payment.amount_signed for payment in uyu_payments):.2f}".replace('.', '')
        ch = '0'
        usd_payments = batch_payment.payment_ids.filtered(lambda p: p.currency_id.name == 'USD')
        ci = str(len(usd_payments))
        cj = f"{sum(payment.amount_signed for payment in usd_payments):.2f}".replace('.', '')
        ck = '0'
        cl = (config_f_vars.get(12) and config_f_vars.get(12).value) or 'AUTOMATICO'

        # SET FIXED SPACES
        ca = ca.rjust(EXPECTED_LENGTHS_VISANET2['ca'], '0')
        cb = cb.rjust(EXPECTED_LENGTHS_VISANET2['cb'], '0')
        cc = cc.rjust(EXPECTED_LENGTHS_VISANET2['cc'], '0')
        cd = cd.rjust(EXPECTED_LENGTHS_VISANET2['cd'], '0')
        ce = ce.rjust(EXPECTED_LENGTHS_VISANET2['ce'], '0')
        cf = cf.rjust(EXPECTED_LENGTHS_VISANET2['cf'], '0')
        cg = cg.rjust(EXPECTED_LENGTHS_VISANET2['cg'], '0')
        ch = ch.rjust(EXPECTED_LENGTHS_VISANET2['ch'], '0')
        ci = ci.rjust(EXPECTED_LENGTHS_VISANET2['ci'], '0')
        cj = cj.rjust(EXPECTED_LENGTHS_VISANET2['cj'], '0')
        ck = ck.rjust(EXPECTED_LENGTHS_VISANET2['ck'], '0')
        cl = cl.rjust(EXPECTED_LENGTHS_VISANET2['cl'], '0')

        c_list = [
            ca, cb, cc, cd, ce, cf, cg, ch, ci, cj, ck, cl
        ]
        separator = self.column_separator or ''
        file += separator.join(c_list) + '\n'

        return {'file': file, '_rslt': _rslt}

    def _check_line_lengths_visanet(self, payment, line_list, EXPECTED_LENGTHS_VISANET, COLUMNS_TITLES_VISANET):
        """
        Verifica que las longitudes de las líneas sean correctas.
        :param payment: Línea del pago.
        :param line_list: Lista de líneas a verificar.
        :return: Lista de errores encontrados.
        """
        _rslt = []

        # Por defecto se espera coincidencia exacta, excepto los que van con máximo permitido
        max_only_keys = {}

        for i, value in enumerate(line_list, start=1):
            key = f'c{i}'
            expected = EXPECTED_LENGTHS_VISANET.get(key)
            if expected is None:
                continue  # en caso de que falte alguna clave
            actual_len = len(value)
            if key in max_only_keys and actual_len > expected:
                _title = _('%s: El campo %s con valor %s excede la longitud máxima permitida de %s') % (
                    self.name,
                    COLUMNS_TITLES_VISANET[key],
                    value,
                    expected
                )
                _rslt.append({
                    'title': _title,
                    'records': payment,
                    'help': _("")
                })
            elif key not in max_only_keys and actual_len != expected:
                _title = _('%s: El campo %s con valor %s no tiene la longitud correcta. Se espera %s') % (
                    self.name,
                    COLUMNS_TITLES_VISANET[key],
                    value,
                    expected
                )
                _rslt.append({
                    'title': _title,
                    'records': payment,
                    'help': _("")
                })
        return _rslt
