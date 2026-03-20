# -*- coding: utf-8 -*-
from odoo import models, _
import calendar
import re
import unicodedata

EXPECTED_LENGTHS = {
    'c1': 5,
    'c2': 1,
    'c3': 4,
    'c4': 16,
    'c5': 8,
    'c6': 1,
    'c7': 22,
    'c8': 3,
    'c9': 50,
    'c10': 1,
    'c11': 12,
    'c12': 30,
    'c13': 5,
    'c14': 19,
    'c15': 5,
    'c16': 1,
    'c17': 19,
    'c18': 1,
    'c19': 14,
    'c20': 50,
    'c21': 10000,
    'c22': 3
}

COLUMNS_TITLES = {
    'c1': 'Versión del registro',
    'c2': 'Forma de pago',
    'c3': 'Código de Moneda',
    'c4': 'Monto a pagar',
    'c5': 'Fecha de pago',
    'c6': 'Tipo cuenta',
    'c7': 'Número de cuenta',
    'c8': 'Código de banco',
    'c9': 'Nombre del Beneficiario',
    'c10': 'Tipo de documento',
    'c11': 'Número de documento',
    'c12': 'Dirección - Calle',
    'c13': 'Dirección - Número',
    'c14': 'Dirección - Localidad',
    'c15': 'Dirección - Código postal',
    'c16': 'Dirección - Código Departamento',
    'c17': 'Teléfono',
    'c18': 'Disponible Descontar',
    'c19': 'Número del proveedor',
    'c20': 'Email del proveedor',
    'c21': 'Texto a incluir en el email a enviar',
    'c22': 'Destino de fondos'
}

EXPECTED_LENGTHS_DEB_AUTO = {
    'c1': 7,  # Número de Cuenta Débito
    'c2': 4,  # Correlativo del cliente
    'c3': 1,  # Tipo de Pago ("3")
    'c4': 7,  # Filler
    'c5': 8,  # Referencia Crédito
    'c6': 4,  # Filler
    'c7': 8,  # Referencia Débito
    'c8': 20,  # Filler
    'c9': 7,  # Número de Cuenta Crédito
    'c10': 4,  # Moneda
    'c11': 15,  # Importe
    'c12': 7,  # Fecha de Pago
    'c13': 2,  # Oficina
    'c14': 1,  # Aplica Ley 19.210
    'c15': 15,  # Monto imponible para cálculo de reducción del IVA
    'c16': 15,  # Filler
    'c17': 20,  # Datos Factura
    'c18': 1  # Cliente incluido en ley 18.083 o 18.874
}

COLUMNS_TITLES_DEB_AUTO = {
    'c1': 'Número de Cuenta Débito',
    'c2': 'Correlativo del cliente',
    'c3': 'Tipo de Pago ("3")',
    'c4': 'Filler (Dejar en blanco)',
    'c5': 'Referencia Crédito',
    'c6': 'Filler (Dejar en blanco)',
    'c7': 'Referencia Débito',
    'c8': 'Filler (Dejar en blanco)',
    'c9': 'Número de Cuenta Crédito',
    'c10': 'Moneda',
    'c11': 'Importe',
    'c12': 'Fecha de Pago',
    'c13': 'Oficina',
    'c14': 'APLICA LEY 19.210',
    'c15': 'MONTO IMPONIBLE PARA CALCULO DE REDUCCION DEL IVA',
    'c16': 'Filler (Dejar en blanco)',
    'c17': 'Datos Factura',
    'c18': 'CLIENTE INCLUIDO LEY 18.083 o 18.874'
}


class AccountBatchPaymentFileConfig(models.Model):
    _inherit = "account.bank.payment.file.config"

    def check_payments_for_errors(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """
        rslt = super(AccountBatchPaymentFileConfig, self).check_payments_for_errors(payments)

        if self.code == "itau":
            itau_rslt = []
            config_vars = {line.sequence: line for line in self.line_ids}

            missing_keys = [k for k in [1, 2, 3, 10, 18, 22] if k not in config_vars]
            for k in missing_keys:
                itau_rslt.append({
                    'title': _("%s: La configuración de archivo de pago no tiene la variable %s configurada.") % (
                        self.name, k),
                    'records': payments,
                    'help': ""
                })
            rslt.extend(itau_rslt)
            rslt.extend(self._get_values_itau(payments).get('itau_rslt', []))

        if self.code == "itau_deb_auto":
            itau_rslt = []
            config_vars = {line.sequence: line for line in self.line_ids}

            missing_keys = [k for k in [2, 3, 7, 9, 10, 14, 18] if k not in config_vars]
            for k in missing_keys:
                itau_rslt.append({
                    'title': _(
                        "%s: La configuración de archivo de pago 'ITAU DEB AUTO' no tiene la variable %s configurada.") % (
                                 self.name, k),
                    'records': payments,
                    'help': ""
                })
            rslt.extend(itau_rslt)
            rslt.extend(self._get_values_itau_deb_auto(payments).get('itau_rslt', []))

        return rslt

    def _generate_payment_file_itau(self, payments):
        """
        Genera una plantilla de pago a partir de los pagos proporcionados para ITAU.

        :param payments: Lista de pagos a procesar.
        :return: Texto para fichero de pago.
        """
        return self._get_values_itau(payments).get('file', '')

    def _get_values_itau(self, payments):
        file = ""
        config_vars = {}
        itau_rslt = []
        for line in self.line_ids:
            config_vars[line.sequence] = line
        for payment in payments:
            line = config_vars.get(1, '')
            c1 = line and line.value or ''
            line = config_vars.get(2, '')
            c2 = line and line.value

            c3 = self._get_mapped_value(
                config_vars.get(3, False),
                payment.currency_id.name,
                COLUMNS_TITLES['c3'],
                payment,
                itau_rslt
            )

            c4 = f"{payment.amount:.2f}".replace('.', '')
            c5 = payment.batch_payment_id.date.strftime('%Y%m%d') if payment.batch_payment_id else ""

            c6_line = config_vars.get(6, False)
            if not c6_line:
                c6 = ""
            elif c6_line.type == 'mapping':
                c_map = dict(pair.split('=') for pair in c6_line.value.split(','))
                c6_keys = dict(payment.partner_bank_id._fields['account_type'].selection)
                c6_odoo = c6_keys.get(payment.partner_bank_id.account_type) or _('No establecido')
                c6 = c_map.get(c6_odoo, '')
                if not c6:
                    itau_rslt.append({
                        'title': _(
                            "La configuración de archivo de pago ITAU no tiene configurado "
                            "correctamente el mapeo para el Tipo de cuenta %s o el Contacto no "
                            "tiene Cuenta configurada. Verifíquelo"
                        ) % c6_odoo,
                        'records': payment,
                        'help': _(""),
                    })
            else:
                c6 = payment.partner_bank_id.account_type or ""

            c7 = str(payment.partner_bank_id.acc_number) if payment.partner_bank_id.acc_number else ' '
            c8 = payment.partner_bank_id.bank_id.bic or ''
            c9 = self.sanitize_str(payment.partner_id.name) or ''

            c10 = self._get_mapped_value(
                config_vars.get(10, False),
                payment.partner_id.l10n_latam_identification_type_id.name,
                COLUMNS_TITLES['c10'],
                payment,
                itau_rslt
            )
            c11 = payment.partner_id.vat or ''
            line = config_vars.get(18, False)
            c18 = line and line.value or ''
            c20 = payment.partner_id.email or ''
            line = config_vars.get(22, False)
            c22 = line and line.value or ''

            # SET FIXED SPACES
            c1 = c1.ljust(EXPECTED_LENGTHS['c1'], ' ')
            c2 = c2.rjust(EXPECTED_LENGTHS['c2'], ' ')
            c3 = c3.ljust(EXPECTED_LENGTHS['c3'], ' ')
            c4 = c4.rjust(EXPECTED_LENGTHS['c4'], ' ')
            c5 = c5.rjust(EXPECTED_LENGTHS['c5'], ' ')
            c6 = c6.rjust(EXPECTED_LENGTHS['c6'], ' ')
            c7 = c7.rjust(EXPECTED_LENGTHS['c7'], ' ')
            c8 = c8.rjust(EXPECTED_LENGTHS['c8'], ' ')
            c9 = c9.ljust(EXPECTED_LENGTHS['c9'], ' ')
            c10 = c10.rjust(EXPECTED_LENGTHS['c10'], ' ')
            c11 = c11.rjust(EXPECTED_LENGTHS['c11'], ' ')
            c12 = ''.rjust(EXPECTED_LENGTHS['c12'], ' ')
            c13 = ''.rjust(EXPECTED_LENGTHS['c13'], ' ')
            c14 = ''.rjust(EXPECTED_LENGTHS['c14'], ' ')
            c15 = ''.rjust(EXPECTED_LENGTHS['c15'], ' ')
            c16 = ''.rjust(EXPECTED_LENGTHS['c16'], ' ')
            c17 = ''.rjust(EXPECTED_LENGTHS['c17'], ' ')
            c18 = c18.rjust(EXPECTED_LENGTHS['c18'], ' ')
            c19 = ''.rjust(EXPECTED_LENGTHS['c19'], ' ')
            c20 = c20.ljust(EXPECTED_LENGTHS['c20'], ' ')
            c21 = ''.rjust(EXPECTED_LENGTHS['c21'], ' ')
            c22 = c22.ljust(EXPECTED_LENGTHS['c22'], ' ')

            c_list = [
                c1, c2, c3, c4, c5, c6, c7, c8, c9, c10,
                c11, c12, c13, c14, c15, c16, c17, c18, c19, c20, c21, c22
            ]
            itau_rslt.extend(self._check_line_lengths_itau(payment, c_list))

            separator = self.column_separator or ''
            file += separator.join(c_list) + '\n'
        return {'file': file, 'itau_rslt': itau_rslt}

    def _check_line_lengths_itau(self, payment, line_list):
        """
        Verifica que las longitudes de las líneas sean correctas.
        :param payment: Línea del pago.
        :param line_list: Lista de líneas a verificar.
        :return: Lista de errores encontrados.
        """
        itau_rslt = []

        # Por defecto se espera coincidencia exacta, excepto los que van con máximo permitido
        max_only_keys = {'c9', 'c20', 'c21'}

        for i, value in enumerate(line_list, start=1):
            key = f'c{i}'
            expected = EXPECTED_LENGTHS.get(key)
            if expected is None:
                continue  # en caso de que falte alguna clave
            actual_len = len(value)
            if key in max_only_keys and actual_len > expected:
                _title = _('%s: El campo %s con valor %s excede la longitud máxima permitida de %s') % (
                    self.name,
                    COLUMNS_TITLES[key],
                    value,
                    expected
                )
                itau_rslt.append({
                    'title': _title,
                    'records': payment,
                    'help': _("")
                })
            elif key not in max_only_keys and actual_len != expected:
                _title = _('%s: El campo %s con valor %s no tiene la longitud correcta. Se espera %s') % (
                    self.name,
                    COLUMNS_TITLES[key],
                    value,
                    expected
                )
                itau_rslt.append({
                    'title': _title,
                    'records': payment,
                    'help': _("")
                })

        return itau_rslt

    def sanitize_str(self, value, length=50):
        if not value:
            return ' ' * length

        # Reemplazo específico para Ñ y ñ
        value = value.replace('Ñ', '#').replace('ñ', '#')

        # Reemplazo específico para ü y Ü
        value = value.replace('ü', 'u').replace('Ü', 'U')

        # Normalizar (quita acentos)
        normalized = unicodedata.normalize('NFKD', value)
        ascii_str = ''.join(
            c for c in normalized if not unicodedata.combining(c)
        )
        # Truncar y rellenar con espacios
        ascii_str = ascii_str[:length].ljust(length, ' ')
        return ascii_str

    def _generate_payment_file_itau_deb_auto(self, payments):
        """
        Genera una plantilla de pago a partir de los pagos proporcionados para ITAU.

        :param payments: Lista de pagos a procesar.
        :return: Texto para fichero de pago.
        """
        return self._get_values_itau_deb_auto(payments).get('file', '')

    def _get_values_itau_deb_auto(self, payments):
        file = ""
        config_vars = {line.sequence: line for line in self.line_ids}
        itau_rslt = []

        for payment in payments:
            invoice_ids = getattr(payment, 'invoice_ids', None)
            invoice = invoice_ids and invoice_ids[0] or None

            # Número de Cuenta Débito
            card_info_dict = self._get_card_info(payment)
            num_tarj = card_info_dict.get('card_number', '')
            num_tarj = '' if not num_tarj else num_tarj.strip()
            if not num_tarj:
                itau_rslt.append({
                    'title': _("El pago %s no tiene número de tarjeta configurado en el afiliado.") % payment.name,
                    'records': payment,
                    'help': ''
                })

            c1 = num_tarj

            # Correlativo del cliente
            c2 = config_vars.get(2).value if config_vars.get(2) else ''

            # Tipo de Pago
            c3 = config_vars.get(3).value if config_vars.get(3) else "3"

            # Filler (Dejar en blanco)
            c4 = ' '

            # Referencia Crédito
            matricula = invoice.commercial_registration if hasattr(invoice, 'commercial_registration') else ''
            c5 = '' if not matricula else matricula

            # Filler (Dejar en blanco)
            c6 = ' '

            # Referencia Débito
            c7 = config_vars.get(7).value if config_vars.get(7) else ''

            # Filler (Dejar en blanco)
            c8 = ' '

            # Número de Cuenta Crédito
            c9 = config_vars.get(9).value if config_vars.get(9) else ''

            # Moneda
            c10 = self._get_mapped_value(
                config_vars.get(10) if config_vars.get(10) else '',
                payment.currency_id.name,
                COLUMNS_TITLES_DEB_AUTO['c10'],
                payment,
                itau_rslt
            )

            # Importe
            c11 = f"{payment.amount:.2f}".replace('.', '')

            # Fecha de Pago
            day = payment.date.strftime('%d')
            year = payment.date.strftime('%y')
            month_abbr = calendar.month_abbr[payment.date.month].upper()
            c12 = f"{day}{month_abbr}{year}"

            # Oficina
            c13 = ' '

            # APLICA LEY 19.210
            if config_vars.get(14) and config_vars.get(14).type == 'mapping':
                aplica = getattr(payment, 'vat_refund_applicable', None)
                aplica_odoo = 'true' if aplica else 'false' if aplica is not None else ''
                c14 = self._get_mapped_value(
                    config_vars.get(14) if config_vars.get(14) else '',
                    aplica_odoo,
                    COLUMNS_TITLES_DEB_AUTO['c14'],
                    payment,
                    itau_rslt
                )
            else:
                c14 = config_vars.get(14).value if config_vars.get(14) else ''

            # MONTO IMPONIBLE PARA CALCULO DE REDUCCION DEL IVA
            # c15 = sum(invoice_ids.mapped('taxable_amount')) or 0.0
            c15 = c11 # Por ahora se envía el mismo monto del pago

            # Filler (Dejar en blanco)
            c16 = ' '

            # Datos Factura
            invoice = invoice_ids[0] if invoice_ids else None
            if invoice:
                issue_date = invoice.invoice_date
                invoice_number_str = invoice.name or ''
                c17 = self.format_invoice_data(issue_date, invoice_number_str)
            else:
                c17 = ' '

            # CLIENTE INCLUIDO LEY 18.083 o 18.874
            c18 = config_vars.get(18).value if config_vars.get(18) else ''

            # SET FIXED SPACES
            c1 = c1[:EXPECTED_LENGTHS_DEB_AUTO['c1']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c1'], '0')
            c2 = c2[:EXPECTED_LENGTHS_DEB_AUTO['c2']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c2'], ' ')
            c3 = c3[:EXPECTED_LENGTHS_DEB_AUTO['c3']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c3'], '0')
            c4 = c4[:EXPECTED_LENGTHS_DEB_AUTO['c4']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c4'], ' ')
            c5 = c5[:EXPECTED_LENGTHS_DEB_AUTO['c5']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c5'], ' ')
            c6 = c6[:EXPECTED_LENGTHS_DEB_AUTO['c6']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c6'], ' ')
            c7 = c7[:EXPECTED_LENGTHS_DEB_AUTO['c7']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c7'], ' ')
            c8 = c8[:EXPECTED_LENGTHS_DEB_AUTO['c8']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c8'], ' ')
            c9 = c9[:EXPECTED_LENGTHS_DEB_AUTO['c9']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c9'], '0')
            c10 = c10[:EXPECTED_LENGTHS_DEB_AUTO['c10']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c10'], ' ')
            c11 = c11[:EXPECTED_LENGTHS_DEB_AUTO['c11']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c11'], '0')
            c12 = c12[:EXPECTED_LENGTHS_DEB_AUTO['c12']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c12'], ' ')
            c13 = c13[:EXPECTED_LENGTHS_DEB_AUTO['c13']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c13'], ' ')
            c14 = c14[:EXPECTED_LENGTHS_DEB_AUTO['c14']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c14'], ' ')
            c15 = c15[:EXPECTED_LENGTHS_DEB_AUTO['c15']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c15'], '0')
            c16 = c16[:EXPECTED_LENGTHS_DEB_AUTO['c16']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c16'], ' ')
            c17 = c17[:EXPECTED_LENGTHS_DEB_AUTO['c17']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c17'], ' ')
            c18 = c18[:EXPECTED_LENGTHS_DEB_AUTO['c18']].rjust(EXPECTED_LENGTHS_DEB_AUTO['c18'], ' ')

            c_list = [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c16, c17, c18]

            separator = self.column_separator or ''
            file += separator.join(c_list) + '\n'
        return {'file': file, 'itau_rslt': itau_rslt}

    def format_invoice_data(self, issue_date, invoice_number_str):
        """
        Convierte los datos de la factura al formato requerido por el banco:
        6 posiciones para la fecha (DDMMAA)
        2 posiciones para la serie (primer carácter espacio o letra, segundo letra)
        12 posiciones para el número de factura (rellenado con ceros a la izquierda)
        """
        # Formatear la fecha: DDMMAA
        formatted_date = issue_date.strftime('%d%m%y')

        # Tomar solo la última parte del string (luego del último espacio)
        clean_str = invoice_number_str.strip().split()[-1]

        # Extraer letras (serie) y números
        match = re.match(r'^([A-Za-z]{1,2})?(\d+)$', clean_str)

        series = match.group(1).upper().rjust(2) if match and match.group(1) else '  '
        number = match.group(2).zfill(12) if match and match.group(2) else '000000000000'

        return f"{formatted_date}{series}{number}"
