# -*- coding: utf-8 -*-

from odoo import models, fields, _

EXPECTED_LENGTHS_AMEX_HEADER = {
    'h1': 1,  # Tipo de registro (H)
    'h2': 8,  # Código de archivo
    'h3': 3,  # Grupo de movimientos
    'h4': 4,  # Longitud registro
    'h5': 3,  # Banco informante
    'h6': 10,  # Cuenta única informante
    'h7': 2,  # Filler
    'h8': 3,  # Código Banco destino
    'h9': 12,  # Filler
    'h10': 8,  # Fecha de generación AAAAMMDD
    'h11': 6,  # Hora de generación HHMMSS
    'h12': 1,  # Tipo proceso
    'h13': 1,  # Rendir lote
    'h14': 10,  # Número de lote
    'h15': 8,  # Fecha de presentación
    'h16': 99,  # Filler
    'h17': 1,  # Fin registro (*)
}

COLUMNS_TITLES_AMEX_HEADER = {
    'h1': 'Tipo de registro',
    'h2': 'Código de archivo',
    'h3': 'Grupo de movimientos',
    'h4': 'Longitud registro',
    'h5': 'Banco informante',
    'h6': 'Cuenta única informante',
    'h7': 'Filler',
    'h8': 'Código Banco destino',
    'h9': 'Filler',
    'h10': 'Fecha de generación',
    'h11': 'Hora de generación',
    'h12': 'Tipo proceso',
    'h13': 'Rendir lote',
    'h14': 'Número de lote',
    'h15': 'Fecha de presentación',
    'h16': 'Filler',
    'h17': 'Fin registro (*)',
}

EXPECTED_LENGTHS_AMEX_LINE = {
    'd1': 1,  # Tipo de registro (D)
    'd2': 6,  # Código de operación
    'd3': 10,  # Número de factura
    'd4': 19,  # Número de tarjeta
    'd5': 8,  # Número de Referencia
    'd6': 8,  # Fecha movimiento
    'd11': 3,  # Moneda
    'd12': 15,  # Importe total
    'd121': 2,  # Filler (espacios)
    'd13': 8,  # Importe Ley Uruguay
    'd131': 2,  # Filler (espacios)
    'd14': 1,  # Indicador de aplicación Ley 19210 (S/N/' ')
    'd15': 4,  # Filler (espacios)
    'd16': 15,  # Punto de venta (RUT empresa)
    'd17': 45,  # Descripción punto de venta (nombre empresa)
    'd18': 2,  # Filler (espacios)
    'd19': 6,  # Número de autorización (vacío)
    'd20': 0,  # Fecha presentación movimiento
    'd21': 2,  # CGDAA-SS-FPRES-MOV (fijo 20)
    'd22': 2,  # CGDAA-AA-FPRES-MOV (año, ej 25)
    'd23': 2,  # CGDAA-MM-FPRES-MOV (mes, ej 09)
    'd24': 2,  # CGDAA-DD-FPRES-MOV (día)
    'd25': 10,  # Valor impuesto 1 - NO aplica → 4 espacios
    'd26': 2,  # Filler (espacio)
    'd27': 4,  # Vencimiento tarjeta (añomes, ej 2509)
    'd28': 2,  # Filler (espacios)
    'd29': 1,  # Fin registro (* fijo)
}

COLUMNS_TITLES_AMEX_LINE = {
    'd1': 'Tipo de registro',
    'd2': 'Código de operación',
    'd3': 'Número de factura',
    'd4': 'Número de tarjeta',
    'd5': 'Número de Referencia',
    'd6': 'Fecha movimiento',
    'd11': 'Moneda',
    'd12': 'Importe total',
    'd13': 'Importe Ley Uruguay',
    'd131': 'Filler (espacios)',
    'd14': 'Indicador Ley 19210',
    'd15': 'Filler (espacios)',
    'd16': 'Punto de venta (RUT empresa)',
    'd17': 'Descripción punto de venta (nombre empresa)',
    'd18': 'Filler (espacios)',
    'd19': 'Número de autorización (vacío)',
    'd20': 'Fecha presentación movimiento',
    'd21': 'CGDAA-SS-FPRES-MOV',
    'd22': 'CGDAA-AA-FPRES-MOV (año)',
    'd23': 'CGDAA-MM-FPRES-MOV (mes)',
    'd24': 'CGDAA-DD-FPRES-MOV (día)',
    'd25': 'Valor impuesto 1 (no aplica, espacios)',
    'd26': 'Filler (espacio)',
    'd27': 'Vencimiento tarjeta (añomes)',
    'd28': 'Filler (espacios)',
    'd29': 'Fin de detalle (*)',
}

EXPECTED_LENGTHS_AMEX_TRAILER = {
    't1': 1,  # Tipo de registro (T)
    't2': 8,  # Código del Archivo
    't3': 3,  # Grupo de Movimientos
    't4': 4,  # Longitud del Registro
    't5': 3,  # Código del Banco Informante
    't6': 10,  # Cuenta Unica Informante
    't7': 2,  # Filler
    't8': 3,  # Código del Banco Destino
    't9': 12,  # Filler
    't10': 8,  # Fecha de generación
    't11': 6,  # Hora de generación
    't12': 1,  # Marca del Tipo de Proceso
    't13': 6,  # Cantidad de Registros Enviados
    't14': 18,  # Importe del los Movimientos Enviados
    't15': 18,  # Importe del los Movimientos Enviados SN
    't16': 76,  # Filler
    't17': 1,  # Fin registro (*)
}

COLUMNS_TITLES_AMEX_TRAILER = {
    't1': 'Tipo de registro',
    't2': 'Código del Archivo',
    't3': 'Grupo de Movimientos',
    't4': 'Longitud del Registro',
    't5': 'Código del Banco Informante',
    't6': 'Cuenta Única Informante',
    't7': 'Filler',
    't8': 'Código del Banco Destino',
    't9': 'Filler',
    't10': 'Fecha de generación',
    't11': 'Hora de generación',
    't12': 'Marca del Tipo de Proceso',
    't13': 'Cantidad de Registros Enviados',
    't14': 'Importe de los Movimientos Enviados',
    't15': 'Importe de los Movimientos Enviados SN',
    't16': 'Filler',
    't17': 'Fin registro (*)',
}


class AccountBatchPaymentFileConfig(models.Model):
    _inherit = "account.bank.payment.file.config"

    def check_payments_for_errors(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """
        rslt = super(AccountBatchPaymentFileConfig, self).check_payments_for_errors(payments)
        if self.code == 'amex':
            amex_rslt = []

            # Variables requeridas encabezado
            config_h_vars = {line.sequence: line for line in self.header_ids}
            missing_keys = [k for k in [1, 2, 3, 5, 6, 8, 11, 17] if k not in config_h_vars]
            for k in missing_keys:
                amex_rslt.append({
                    'title': _("La variable %s no está configurada en el encabezado del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

            # Variables requeridas cuerpo
            config_l_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [1, 2, 11, 14, 16, 29] if k not in config_l_vars]
            for k in missing_keys:
                amex_rslt.append({
                    'title': _("La variable %s no está configurada en las líneas del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

            # Variables requeridas linea cierre
            config_t_vars = {line.sequence: line for line in self.footer_ids}
            missing_keys = [k for k in [1, 2, 3, 5, 6, 8, 17] if k not in config_t_vars]
            for k in missing_keys:
                amex_rslt.append({
                    'title': _("La variable %s no está configurada la línea de cierre del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

            values = self._get_values_amex(payments)
            amex_rslt.extend(values.get('amex_rslt', []))
            rslt.extend(amex_rslt)
        return rslt

    def _generate_payment_file_amex(self, payments):
        return self._get_values_amex(payments).get('file', '')

    def _get_values_amex(self, payments):
        """
        Genera un archivo AMEX con estructura:
        - Encabezado
        - Líneas de detalle (una por cada payment)
        - Trailer de cierre
        """
        amex_rslt = []
        file_content = ""
        separator = self.column_separator or ''

        # 1. Encabezado
        header = self._build_amex_header(payments, separator)
        file_content += header + "\n"

        # 2. Líneas de detalle
        for payment in payments:
            line = self._build_amex_line(payment, separator, amex_rslt)
            file_content += line + "\n"

        # 3. Líneas de cierre
        trailer = self._build_amex_trailer(payments, separator)
        file_content += trailer + "\n"

        return {"file": file_content, "amex_rslt": amex_rslt}

    # ======================
    # ENCABEZADO
    # ======================
    def _build_amex_header(self, payments, separator):
        config_h_vars = {line.sequence: line for line in self.header_ids}

        # Tipo de registro
        h1_value = config_h_vars.get(1).value if config_h_vars.get(1) else " "
        h1 = self._format_field_amex_header(h1_value, "h1")

        # Código archivo (ejemplo fijo)
        h2_value = config_h_vars.get(2).value if config_h_vars.get(2) else " "
        h2 = self._format_field_amex_header(h2_value, "h2", padding=' ', just='left')

        # Grupo movimientos
        h3_value = config_h_vars.get(3).value if config_h_vars.get(3) else " "
        h3 = self._format_field_amex_header(h3_value, "h3")

        # Longitud registro
        h4_value = "180"
        h4 = self._format_field_amex_header(h4_value, "h4", padding='0')

        # Banco informante
        h5_value = config_h_vars.get(5).value if config_h_vars.get(5) else " "
        h5 = self._format_field_amex_header(h5_value, "h5")

        # Cuenta única
        h6_value = config_h_vars.get(6).value if config_h_vars.get(6) else " "
        h6 = self._format_field_amex_header(h6_value, "h6")

        # Filler
        h7 = self._format_field_amex_header("", "h7")

        # Banco destino
        h8_value = config_h_vars.get(8).value if config_h_vars.get(8) else " "
        h8 = self._format_field_amex_header(h8_value, "h8")

        # Filler
        h9 = self._format_field_amex_header("", "h9")

        # Fecha de generación AAAAMMDD
        batch_date = (
            payments[0].batch_payment_id.date
            if payments and payments[0].batch_payment_id and payments[0].batch_payment_id.date
            else None
        )
        h10_value = batch_date.strftime("%Y%m%d") if batch_date else ""
        h10 = self._format_field_amex_header(h10_value, "h10")

        # Hora de generación HHMMSS
        h11_value = config_h_vars.get(11).value if config_h_vars.get(11) else " "
        h11 = self._format_field_amex_header(h11_value, "h11")

        # Tipo proceso
        h12_value = " "
        h12 = self._format_field_amex_header(h12_value, "h12")

        # Rendir lote
        h13_value = " "
        h13 = self._format_field_amex_header(h13_value, "h13")

        # Número lote
        batch_name = (
            payments[0].batch_payment_id.name
            if payments and payments[0].batch_payment_id and payments[0].batch_payment_id.name
            else " "
        )
        h14_value = self.get_batch_number_amex(batch_name)
        h14 = self._format_field_amex_header(h14_value, "h14", padding='0')

        # Fecha de presentación
        h15 = h10  # Misma que fecha de generación

        # Filler
        h16 = self._format_field_amex_header("", "h16")

        # Fin registro
        h17_value = config_h_vars.get(17).value if config_h_vars.get(17) else " "
        h17 = self._format_field_amex_header(h17_value, "h17")

        return separator.join([
            h1, h2, h3, h4, h5, h6, h7, h8, h9,
            h10, h11, h12, h13, h14, h15, h16, h17
        ])

    # ======================
    # DETALLE (una línea por pago)
    # ======================
    def _build_amex_line(self, payment, separator, amex_rslt):
        invoice_ids = getattr(payment, "invoice_ids", None)
        invoice = invoice_ids[0] if invoice_ids else None
        config_l_vars = {line.sequence: line for line in self.line_ids}

        # Tipo de registro
        d1_value = config_l_vars.get(1).value if config_l_vars.get(1) else " "
        d1 = self._format_field_amex(d1_value, "d1")

        # Código operación
        d2_value = config_l_vars.get(2).value if config_l_vars.get(2) else " "
        d2 = self._format_field_amex(d2_value, "d2")

        # Número de factura
        d3_value = self.get_invoice_amex(invoice.name) if invoice else ''
        d3 = self._format_field_amex(d3_value, "d3", padding=' ')

        # Número de tarjeta
        card_info_dict = self._get_card_info(payment)
        num_tarj = str(card_info_dict.get('card_number') or '').strip()
        if not num_tarj:
            amex_rslt.append({
                'title': _("El pago %s no tiene número de tarjeta configurado en el afiliado.") % payment.name,
                'records': payment,
                'help': ''
            })

        d4 = self._format_field_amex(num_tarj, "d4", padding='0', just='left')

        # Referencia (número interno del pago)
        d5_value = self.get_payment_number_amex(payment.name)
        d5 = self._format_field_amex(d5_value, "d5", padding='0')

        # Fecha de movimiento
        d6 = self._format_field_amex(payment.date.strftime("%Y%m%d"), "d6")

        # Moneda
        if config_l_vars.get(11) and config_l_vars.get(11).type == 'mapping':
            d11_value = self._get_mapped_value(
                config_l_vars.get(11),
                payment.currency_id.name,
                COLUMNS_TITLES_AMEX_LINE['d11'],
                payment,
                amex_rslt
            )
        else:
            d11_value = config_l_vars.get(11).value if config_l_vars.get(11) else " "

        d11 = self._format_field_amex(d11_value, "d11")

        # Importe total (sin separador decimal)
        d12_value = f"{payment.amount:.2f}".replace(".", "")
        d12 = self._format_field_amex(d12_value, "d12", padding='0')

        # Filler 2 (espacios)
        d121 = self._format_field_amex(" ", "d121")

        # Importe Ley Uruguay (sin separador decimal)
        d13_value = sum(invoice_ids.mapped('taxable_amount')) if invoice_ids else 0.0
        d13_value = f"{d13_value:.2f}".replace(".", "")
        d13 = self._format_field_amex(d13_value, "d13", padding='0')

        # Filler (espacios)
        # d131 = self._format_field_amex("", "d131")

        # Indicador aplicación Ley 19210
        if config_l_vars.get(14) and config_l_vars.get(14).type == 'mapping':
            aplica = getattr(payment, 'vat_refund_applicable', None)
            aplica_odoo = 'true' if aplica else 'false' if aplica is not None else ''
            d14_value = self._get_mapped_value(
                config_l_vars.get(14) if config_l_vars.get(14) else '',
                aplica_odoo,
                COLUMNS_TITLES_AMEX_LINE['d14'],
                payment,
                amex_rslt
            )
        else:
            d14_value = config_l_vars.get(14).value if config_l_vars.get(14) else ''

        d14 = self._format_field_amex(d14_value, "d14")

        # Filler (espacios)
        d15 = self._format_field_amex("", "d15")

        # RUT de la empresa
        d16_value = config_l_vars.get(16).value if config_l_vars.get(16) else " "
        d16 = self._format_field_amex(d16_value, "d16", padding=' ', just='left')

        # Nombre de la empresa
        d17 = self._format_field_amex(payment.company_id.name or "", "d17", padding=' ', just='left')

        # Filler (espacios)
        d18 = self._format_field_amex("", "d18")

        # Número de autorización (vacío)
        d19 = self._format_field_amex("", "d19")

        # Día de presentación del movimiento
        d20 = self._format_field_amex("", "d20")

        # CGDAA-SS-FPRES-MOV
        d21_value = payment.date.strftime("%Y")[:2]
        d21 = self._format_field_amex(d21_value, "d21")

        # Año (2 dígitos)
        d22 = self._format_field_amex(payment.date.strftime("%y"), "d22")

        # Mes (2 dígitos)
        d23 = self._format_field_amex(payment.date.strftime("%m"), "d23")

        # Día (2 dígitos)
        d24 = self._format_field_amex(payment.date.strftime("%d"), "d24")

        # Valor impuesto (no aplica → espacios)
        d25 = self._format_field_amex("", "d25")

        # Filler (espacio)
        d26 = self._format_field_amex("", "d26")

        # Vencimiento de tarjeta (año,mes, obtenido del afiliado)
        # card_exp_month = card_info_dict.get('card_exp_month', '')
        # card_exp_year = card_info_dict.get('card_exp_year', '')
        # d29_value = f"{card_exp_year}{card_exp_month}" if card_exp_year and card_exp_month else ''
        # d27 = self._format_field_amex(d29_value, "d27")
        d27 = self._format_field_amex("", "d27")

        # Filler (espacios)
        d28 = self._format_field_amex("", "d28")

        # Fin registro (* fijo)
        d29_value = config_l_vars.get(29).value if config_l_vars.get(29) else " "
        d29 = self._format_field_amex(d29_value, "d29")

        return separator.join([
            d1, d2, d3, d4, d5, d6, d11, d12, d121, d13,
            d14, d15, d16, d17, d18, d19, d20, d21,
            d22, d23, d24, d25, d26, d27, d28, d29
        ])

    # ======================
    # LINEA DE CIERRE
    # ======================
    def _build_amex_trailer(self, payments, separator):
        config_t_vars = {line.sequence: line for line in self.footer_ids}
        config_h_vars = {line.sequence: line for line in self.header_ids}

        # Tipo de registro
        t1_value = config_t_vars.get(1).value if config_t_vars.get(1) else " "
        t1 = self._format_field_amex_trailer(t1_value, "t1")

        # Código del Archivo
        t2_value = config_t_vars.get(2).value if config_t_vars.get(2) else " "
        t2 = self._format_field_amex_trailer(t2_value, "t2", padding='', just='left')

        # Grupo de Movimientos
        t3_value = config_t_vars.get(3).value if config_t_vars.get(3) else " "
        t3 = self._format_field_amex_trailer(t3_value, "t3")

        # Longitud del Registro
        t4 = self._format_field_amex_trailer("180", "t4", padding="0")

        # Código Banco Informante
        t5_value = config_t_vars.get(5).value if config_t_vars.get(5) else " "
        t5 = self._format_field_amex_trailer(t5_value, "t5")

        # Cuenta Única Informante
        t6_value = config_t_vars.get(6).value if config_t_vars.get(6) else " "
        t6 = self._format_field_amex_trailer(t6_value, "t6")

        # Filler
        t7 = self._format_field_amex_trailer("", "t7")

        # Banco destino
        t8_value = config_t_vars.get(8).value if config_t_vars.get(8) else " "
        t8 = self._format_field_amex_trailer(t8_value, "t8")

        # Filler
        t9 = self._format_field_amex_trailer("", "t9")

        # Fecha de generación
        batch_date = (
            payments[0].batch_payment_id.date
            if payments and payments[0].batch_payment_id and payments[0].batch_payment_id.date
            else None
        )
        t10_value = batch_date.strftime("%Y%m%d") if batch_date else ""
        t10 = self._format_field_amex_trailer(t10_value, "t10")

        # hora generación
        h11_value = config_h_vars.get(11).value if config_h_vars.get(11) else " "
        t11 = self._format_field_amex_trailer(h11_value, "t11")

        # Marca del Tipo de Proceso
        t12_value = ""
        t12 = self._format_field_amex_trailer(t12_value, "t12")

        # Cantidad de Registros Enviados
        t13 = self._format_field_amex_trailer(str(len(payments)), "t13", padding="0")

        # Importe del los Movimientos Enviados
        t14_value = f"{sum(p.amount for p in payments):.2f}".replace(".", "")
        t14 = self._format_field_amex_trailer(t14_value, "t14", padding="0")

        # Importe del los Movimientos Enviadosn SN
        t15_value = ""
        t15 = self._format_field_amex_trailer(t15_value, "t15", padding="")

        # Filler
        t16 = self._format_field_amex_trailer("", "t16")

        # Fin registro
        t17_value = config_t_vars.get(17).value if config_t_vars.get(17) else " "
        t17 = self._format_field_amex_trailer(t17_value, "t17")

        return separator.join([t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17])

    # ======================
    # UTILIDADES
    # ======================
    def _format_field_amex_header(self, value, field_name, padding=' ', just='right'):
        return self._format_field_amex(value, field_name, padding, just, 'header')

    def _format_field_amex_trailer(self, value, field_name, padding=' ', just='right'):
        return self._format_field_amex(value, field_name, padding, just, 'trailer')

    def _format_field_amex(self, value, field_name, padding=' ', just='right', env_context='line'):
        contexts = {
            'header': EXPECTED_LENGTHS_AMEX_HEADER,
            'line': EXPECTED_LENGTHS_AMEX_LINE,
            'trailer': EXPECTED_LENGTHS_AMEX_TRAILER,
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

    def get_batch_number_amex(self, batch_name: str) -> str:
        """
        Extracts the batch number from a batch name.
        Example: 'BATCH/OUT/2025/0055' -> '0055'

        :param batch_name: Full batch name string
        :return: Batch number (last segment of the string) or empty string if invalid
        """
        if not batch_name:
            return ""

        parts = batch_name.strip().split("/")
        return parts[-1] if parts else ""

    def get_payment_number_amex(self, payment_name: str) -> str:
        """
        Extracts the payment number from a payment name.
        Example: 'PBAN3/2025/00073' -> '00073'

        :param payment_name: Full payment name string
        :return: payment number (last segment of the string) or empty string if invalid
        """
        if not payment_name:
            return ""

        if '/' in payment_name:
            ref = payment_name.split('/')[-1]
        else:
            ref = ''.join(c for c in payment_name if c.isdigit())

        return ref

    def get_invoice_amex(self, invoice_number_str):
        # Tomar solo la última parte del string
        clean_str = invoice_number_str.strip().split()[-1]

        return clean_str.replace(" ", "") if clean_str else ''
