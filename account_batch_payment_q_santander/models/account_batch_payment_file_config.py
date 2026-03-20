# -*- coding: utf-8 -*-

import re
from odoo import models, _

EXPECTED_LENGTHS_SANTANDER_DETAIL = {
    'd1': 1, 'd2': 1, 'd3': 3, 'd4': 2, 'd5': 6,
    'd6': 15, 'd7': 20, 'd8': 4, 'd9': 15, 'd10': 13,
    'd11': 2, 'd12': 15, 'd13': 28, 'd14': 3, 'd15': 1,
    'd16': 3, 'd17': 12, 'd18': 15, 'd19': 13, 'd20': 48
}

COLUMNS_TITLES_SANTANDER_DETAIL = {
    'd1': 'Constante “1”',
    'd2': 'Espacio',
    'd3': 'Código de Banco “137”',
    'd4': 'Letras del convenio',
    'd5': 'Fecha de débito “aammdd”',
    'd6': 'Identificación del servicio',
    'd7': 'Cuenta Bancaria',
    'd8': 'Fecha producción “aamm”',
    'd9': 'Importe a debitar',
    'd10': 'Ceros',
    'd11': 'Ciclo “01”',
    'd12': 'Espacios',
    'd13': 'Nombre del Banco',
    'd14': 'Código de Banco “137”',
    'd15': 'Indicador devolución de IVA',
    'd16': 'Serie de la factura',
    'd17': 'Número de la factura',
    'd18': 'Importe gravado',
    'd19': 'Ceros',
    'd20': 'Espacios',
}

EXPECTED_LENGTHS_SANTANDER_TRAILER = {
    't1': 1, 't2': 1, 't3': 3, 't4': 2, 't5': 6, 't6': 6, 't7': 18,
    't8': 6, 't9': 18, 't10': 6, 't11': 18, 't12': 16, 't13': 27,
    't14': 18, 't15': 16, 't16': 6, 't17': 52
}

COLUMNS_TITLES_SANTANDER_TRAILER = {
    't1': 'Constante “2”',
    't2': 'Espacio',
    't3': 'Código de Banco “137”',
    't4': 'Letras del convenio',
    't5': 'Fecha de débito “aammdd”',
    't6': 'Cantidad de facturas a debitar',
    't7': 'Importe a debitar',
    't8': 'Ceros',
    't9': 'Ceros',
    't10': 'Ceros',
    't11': 'Ceros',
    't12': 'Ceros',
    't13': 'Ceros',
    't14': 'Importe gravado',
    't15': 'Ceros',
    't16': 'Ceros',
    't17': 'Espacios',
}


class AccountBatchPaymentFileConfig(models.Model):
    _inherit = "account.bank.payment.file.config"

    def check_payments_for_errors(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """
        rslt = super(AccountBatchPaymentFileConfig, self).check_payments_for_errors(payments)
        if self.code == 'santander_deb_auto':
            santander_rslt = []

            # Variables requeridas cuerpo
            config_l_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [1, 3, 4, 11, 13, 14, 15] if k not in config_l_vars]
            for k in missing_keys:
                santander_rslt.append({
                    'title': _("La variable %s no está configurada en las líneas del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

            # Variables requeridas linea cierre
            config_t_vars = {line.sequence: line for line in self.footer_ids}
            missing_keys = [k for k in [1, 3, 4] if k not in config_t_vars]
            for k in missing_keys:
                santander_rslt.append({
                    'title': _("La variable %s no está configurada en la línea de cierre del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

            values = self._get_values_santander_deb_auto(payments)
            santander_rslt.extend(values.get('santander_rslt', []))
            rslt.extend(santander_rslt)
        return rslt

    def _generate_payment_file_santander_deb_auto(self, payments):
        return self._get_values_santander_deb_auto(payments).get('file', '')

    def _get_values_santander_deb_auto(self, payments):
        """
        Genera un archivo Santander Débitos Automáticos con estructura:
        - Líneas de detalle (una por cada pago)
        - Línea de cierre
        """
        santander_rslt = []
        file_content = ""
        separator = self.column_separator or ''

        # 1. Líneas de detalle
        for payment in payments:
            line = self._build_santander_line(payment, separator, santander_rslt)
            file_content += line + "\n"

        # 2. Línea de cierre
        trailer = self._build_santander_trailer(payments, separator, santander_rslt)
        file_content += trailer + "\n"

        return {"file": file_content, "santander_rslt": santander_rslt}

    # ======================
    # LINEA DE CIERRE
    # ======================
    def _build_santander_trailer(self, payments, separator, santander_rslt):
        payment = payments[0] if payments else None
        config_t_vars = {line.sequence: line for line in self.footer_ids}

        total = sum(p.amount for p in payments)
        total_gravado = sum(sum(p.invoice_ids.mapped('taxable_amount')) for p in payments if p.invoice_ids)

        # Constante “2”
        t1_value = config_t_vars.get(1).value if config_t_vars.get(1) else "2"
        t1 = self._format_field_santander_trailer(t1_value, "t1", padding=' ', just='right')

        # Espacio
        t2_value = " "
        t2 = self._format_field_santander_trailer(t2_value, "t2", padding=' ', just='right')

        # Código de Banco “137”
        t3_value = config_t_vars.get(3).value if config_t_vars.get(3) else "137"
        t3 = self._format_field_santander_trailer(t3_value, "t3", padding=' ', just='right')

        # Letras del convenio
        if config_t_vars.get(1) and config_t_vars.get(4).type == 'mapping':
            t4 = self._get_mapped_value_santander(
                config_t_vars.get(4, False),
                payment.company_id.vat,
                COLUMNS_TITLES_SANTANDER_TRAILER['t4'],
                payment,
                santander_rslt
            )
        else:
            t4_value = config_t_vars.get(4).value if config_t_vars.get(4) else ""
            t4_value = t4_value.upper()
            t4 = self._format_field_santander_trailer(t4_value, "t4", padding=' ', just='right')

        # Fecha de débito
        batch_date = (
            payment.batch_payment_id.date
            if payment and payment.batch_payment_id and payment.batch_payment_id.date
            else None
        )
        t5_value = batch_date.strftime('%y%m%d') if batch_date else ""
        t5 = self._format_field_santander_trailer(t5_value, "t5", padding=' ', just='right')

        # Cantidad de facturas a debitar
        t6_value = str(len(payments))
        t6 = self._format_field_santander_trailer(t6_value, "t6", padding='0', just='right')

        # Importe a debitar
        t7_value = f"{total:.2f}".replace('.', '')
        t7 = self._format_field_santander_trailer(t7_value, "t7", padding='0', just='right')

        # Campos de ceros y espacios
        t8 = self._format_field_santander_trailer('0', "t8", padding='0', just='right')
        t9 = self._format_field_santander_trailer('0', "t9", padding='0', just='right')
        t10 = self._format_field_santander_trailer('0', "t10", padding='0', just='right')
        t11 = self._format_field_santander_trailer('0', "t11", padding='0', just='right')
        t12 = self._format_field_santander_trailer('0', "t12", padding='0', just='right')
        t13 = self._format_field_santander_trailer('0', "t13", padding='0', just='right')

        # Importe gravado
        t14_value = f"{total_gravado:.2f}".replace('.', '')
        t14 = self._format_field_santander_trailer(t14_value, "t14", padding='0', just='right')

        # Ceros finales
        t15 = self._format_field_santander_trailer('0', "t15", padding='0', just='right')
        t16 = self._format_field_santander_trailer('0', "t16", padding='0', just='right')
        t17 = self._format_field_santander_trailer(' ', "t17", padding=' ', just='right')

        return separator.join([
            t1, t2, t3, t4, t5, t6, t7, t8, t9, t10,
            t11, t12, t13, t14, t15, t16, t17
        ])

    # ======================
    # DETALLE (una línea por pago)
    # ======================
    def _build_santander_line(self, payment, separator, santander_rslt):
        invoices = payment.invoice_ids
        invoice = invoices[0] if invoices else None
        config_l_vars = {line.sequence: line for line in self.line_ids}

        # Constante “1”
        d1_value = config_l_vars.get(1).value if config_l_vars.get(1) else "1"
        d1 = self._format_field_santander(d1_value, "d1", padding=' ', just='right', env_context='line')

        # Espacio
        d2_value = " "
        d2 = self._format_field_santander(d2_value, "d2", padding=' ', just='right', env_context='line')

        # Código de Banco “137”
        d3_value = config_l_vars.get(3).value if config_l_vars.get(3) else "137"
        d3 = self._format_field_santander(d3_value, "d3", padding=' ', just='right', env_context='line')

        # Letras del convenio
        if config_l_vars.get(1) and config_l_vars.get(4).type == 'mapping':
            d4 = self._get_mapped_value_santander(
                config_l_vars.get(4, False),
                payment.company_id.vat,
                COLUMNS_TITLES_SANTANDER_DETAIL['d4'],
                payment,
                santander_rslt
            )
        else:
            d4_value = config_l_vars.get(4).value if config_l_vars.get(4) else ""
            d4_value = d4_value.upper()
            d4 = self._format_field_santander(d4_value, "d4", padding=' ', just='right', env_context='line')

        # Fecha de débito (aammdd)
        batch_date = (
            payment.batch_payment_id.date
            if payment and payment.batch_payment_id and payment.batch_payment_id.date
            else None
        )
        d5_value = batch_date.strftime('%y%m%d') if batch_date else ""
        d5 = self._format_field_santander(d5_value, "d5", padding=' ', just='right', env_context='line')

        # Identificación del servicio
        convenio = invoice.agreement_id.code if hasattr(invoice, 'agreement_id') else '0'
        matricula = invoice.commercial_registration if hasattr(invoice, 'commercial_registration') else '0'
        convenio = convenio.rjust(5, "0")
        matricula = matricula.rjust(10, "0")
        d6_value = f"{convenio}{matricula}"
        d6 = self._format_field_santander(d6_value, "d6", padding='0', just='right', env_context='line')

        # Cuenta Bancaria
        # d7_value = str(payment.partner_bank_id.acc_number) if payment.partner_bank_id and payment.partner_bank_id.acc_number else ""
        d7 = self._format_field_santander(" ", "d7", padding=' ', just='right', env_context='line')

        # Fecha producción (aamm)
        d8_value = batch_date.strftime('%y%m') if batch_date else ""
        d8 = self._format_field_santander(d8_value, "d8", padding=' ', just='right', env_context='line')

        # Importe a debitar
        d9_value = f"{payment.amount:.2f}".replace('.', '')
        d9 = self._format_field_santander(d9_value, "d9", padding='0', just='right', env_context='line')

        # Ceros
        d10_value = '0'
        d10 = self._format_field_santander(d10_value, "d10", padding='0', just='right', env_context='line')

        # Ciclo “01”
        d11_value = config_l_vars.get(11).value if config_l_vars.get(11) else "01"
        d11 = self._format_field_santander(d11_value, "d11", padding=' ', just='right', env_context='line')

        # Espacios
        d12_value = ""
        d12 = self._format_field_santander(d12_value, "d12", padding=' ', just='right', env_context='line')

        # Nombre del Banco
        d13_value = config_l_vars.get(13).value if config_l_vars.get(13) else "SANTANDER"
        d13 = self._format_field_santander(d13_value, "d13", padding=' ', just='left', env_context='line')

        # Código Banco
        d14_value = config_l_vars.get(14).value if config_l_vars.get(14) else "137"
        d14 = self._format_field_santander(d14_value, "d14", padding=' ', just='right', env_context='line')

        # Indicador devolución de IVA
        if config_l_vars.get(15) and config_l_vars.get(15).type == 'mapping':
            aplica = getattr(payment, 'vat_refund_applicable', None)
            aplica_odoo = 'true' if aplica else 'false' if aplica is not None else ''
            d15_value = self._get_mapped_value(
                config_l_vars.get(15) if config_l_vars.get(15) else '',
                aplica_odoo,
                COLUMNS_TITLES_SANTANDER_DETAIL['d15'],
                payment,
                santander_rslt
            )
        else:
            d15_value = config_l_vars.get(15).value if config_l_vars.get(15) else ''
        d15 = self._format_field_santander(d15_value, "d15", padding=' ', just='right', env_context='line')

        # Serie de la factura
        d16_value, d17_value = self.get_invoice_santander(invoice.name) if invoice else ('', '')
        d16 = self._format_field_santander(d16_value+" ", "d16", padding=' ', just='right', env_context='line')

        # Número de la factura
        d17 = self._format_field_santander(d17_value, "d17", padding='0', just='right', env_context='line')

        # Importe gravado
        d18_value = sum(invoices.mapped('taxable_amount')) if invoices else 0.0
        d18_value = f"{d18_value:.2f}".replace(".", "")
        d18 = self._format_field_santander(d18_value, "d18", padding='0', just='right', env_context='line')

        # Ceros
        d19_value = '0'
        d19 = self._format_field_santander(d19_value, "d19", padding='0', just='right', env_context='line')

        # Espacios
        d20_value = ""
        d20 = self._format_field_santander(d20_value, "d20", padding=' ', just='right', env_context='line')

        return separator.join([
            d1, d2, d3, d4, d5, d6, d7, d8, d9, d10,
            d11, d12, d13, d14, d15, d16, d17, d18, d19, d20
        ])

    # ======================
    # UTILIDADES
    # ======================
    def _format_field_santander_trailer(self, value, field_name, padding=' ', just='right'):
        return self._format_field_santander(value, field_name, padding, just, 'trailer')

    def _format_field_santander(self, value, field_name, padding=' ', just='right', env_context='line'):
        contexts = {
            'line': EXPECTED_LENGTHS_SANTANDER_DETAIL,
            'trailer': EXPECTED_LENGTHS_SANTANDER_TRAILER,
        }
        lengths = contexts.get(env_context)
        length = lengths[field_name]
        # Si el padding no es válido, usar espacio por defecto
        if not padding or len(padding) != 1:
            padding = ' '

        value_str = str(value)[:length]

        if just == 'right':
            return value_str.rjust(length, padding)
        else:
            return value_str.ljust(length, padding)

    def get_invoice_santander(self, invoice_number_str):
        # Tomar solo la última parte del string
        clean_str = invoice_number_str.strip().split()[-1]

        # Extraer letras (serie) y números
        match = re.match(r'^([A-Za-z]{1,2})?(\d+)$', clean_str)
        if not match:
            return re.sub(r'\D', '', clean_str)

        serie = match.group(1).upper() if match and match.group(1) else ''
        number = match.group(2) if match and match.group(2) else ''

        return serie, number

    def _get_mapped_value_santander(self, config_line, odoo_value, column_title, payment, result_list):
        _base_title = _("%s:La configuración no pudo identificar el mapeo para el campo %s con valor %s")
        if not config_line:
            return ""
        elif config_line.type == 'mapping':
            try:
                c_map = dict(pair.split('=') for pair in config_line.value.split(','))
            except Exception as e:
                c_map = {}
                result_list.append({
                    'title': _base_title % (self.name, column_title, odoo_value),
                    'records': payment,
                    'help_message': _("La configuración del mapeo no es adecuada. Debe ser similar a: valor_odoo1:valor_archivo1,valor_odoo2:valor_archivo2,etc.")
                })
            return c_map.get(odoo_value, " ")
        else:
            return config_line.value or ""
