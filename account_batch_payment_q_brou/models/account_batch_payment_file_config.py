# -*- coding: utf-8 -*-

from odoo import models, _

# ================================
# LONGITUDES Y TITULOS - DETALLE
# ================================
EXPECTED_LENGTHS_BROU_DETAIL = {
    'd1': 1,  # Tipo Registro
    'd2': 1,  # Marca
    'd3': 3,  # Banco
    'd4': 2,  # Filler
    'd5': 6,  # Fecha de vencimiento
    'd6': 15,  # Referencia de servicio
    'd7': 6,  # Convenio
    'd8': 2,  # Moneda
    'd9': 1,  # Código del registro
    'd10': 11,  # Filler
    'd11': 4,  # Fecha de producción
    'd12': 15,  # Importe
    'd13': 13,  # Filler
    'd14': 48,  # Información empresa
    'd15': 12,  # Identificador factura
    'd16': 1,  # Consumidor final
    'd17': 15,  # Importe gravado IVA básico
    'd18': 15,  # Importe gravado IVA mínimo
    'd19': 15,  # Importe devolución de IVA
}

COLUMNS_TITLES_BROU_DETAIL = {
    'd1': 'Tipo de registro',
    'd2': 'Marca',
    'd3': 'Código de Banco',
    'd4': 'Filler',
    'd5': 'Fecha de vencimiento',
    'd6': 'Referencia de servicio',
    'd7': 'Convenio',
    'd8': 'Moneda',
    'd9': 'Código de registro',
    'd10': 'Filler',
    'd11': 'Fecha de producción',
    'd12': 'Importe',
    'd13': 'Filler',
    'd14': 'Información empresa',
    'd15': 'Identificador factura',
    'd16': 'Consumidor final',
    'd17': 'Importe gravado IVA básico',
    'd18': 'Importe gravado IVA mínimo',
    'd19': 'Importe devolución de IVA',
}

# ================================
# LONGITUDES Y TITULOS - TOTALES
# ================================
EXPECTED_LENGTHS_BROU_TRAILER = {
    't1': 1,  # Tipo de registro
    't2': 1,  # Marca
    't3': 3,  # Banco
    't4': 2,  # Filler
    't5': 6,  # Fecha de vencimiento
    't6': 6,  # Facturas a debitar
    't7': 18,  # Importe total a debitar
    't8': 6,  # Cantidad de facturas
    't9': 18,  # Importe total debitado
    't10': 6,  # Facturas no debitadas
    't11': 18,  # Importe total no debitado
    't12': 16,  # Total comisiones BROU
    't13': 16,  # IVA
    't14': 11,  # Información empresa
    't15': 18,  # Importe total gravado IVA básico
    't16': 18,  # Importe total gravado IVA mínimo
    't17': 18,  # Importe devolución de IVA
    't18': 4,  # Filler
}

COLUMNS_TITLES_BROU_TRAILER = {
    't1': 'Tipo de registro',
    't2': 'Marca (espacio en blanco)',
    't3': 'Código de Banco',
    't4': 'Filler',
    't5': 'Fecha de vencimiento',
    't6': 'Facturas a debitar',
    't7': 'Importe total a debitar',
    't8': 'Cantidad de facturas (Constante ceros)',
    't9': 'Importe total debitado (Constante ceros)',
    't10': 'Facturas no debitadas (Constante ceros)',
    't11': 'Importe total no debitado (Constante ceros)',
    't12': 'Total comisiones cobradas por BROU (Constante ceros)',
    't13': 'IVA (Constante ceros)',
    't14': 'Información empresa',
    't15': 'Importe total gravado IVA básico',
    't16': 'Importe total gravado IVA mínimo',
    't17': 'Importe devolución de IVA',
    't18': 'Filler',
}


class AccountBatchPaymentFileConfig(models.Model):
    _inherit = "account.bank.payment.file.config"

    def check_payments_for_errors(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """
        rslt = super(AccountBatchPaymentFileConfig, self).check_payments_for_errors(payments)
        if self.code == 'brou_deb_auto':
            brou_rslt = []

            # Variables requeridas cuerpo
            config_l_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [1, 3, 7, 8, 9] if k not in config_l_vars]
            for k in missing_keys:
                brou_rslt.append({
                    'title': _("La variable %s no está configurada en las líneas del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

            # Variables requeridas linea cierre
            config_t_vars = {line.sequence: line for line in self.footer_ids}
            missing_keys = [k for k in [1, 3, 14] if k not in config_t_vars]
            for k in missing_keys:
                brou_rslt.append({
                    'title': _("La variable %s no está configurada en la línea de cierre del archivo de pago.") % k,
                    'records': payments,
                    'help': ''
                })

            values = self._get_values_brou_deb_auto(payments)
            brou_rslt.extend(values.get('brou_rslt', []))
            rslt.extend(brou_rslt)
        return rslt

    def _generate_payment_file_brou_deb_auto(self, payments):
        return self._get_values_brou_deb_auto(payments).get('file', '')

    def _get_values_brou_deb_auto(self, payments):
        """
        Genera un archivo Brou Débitos Automáticos con estructura:
        - Líneas de detalle (una por cada pago)
        - Línea de cierre
        """
        brou_rslt = []
        file_content = ""
        separator = self.column_separator or ''

        # 1. Líneas de detalle
        for payment in payments:
            line = self._build_brou_line(payment, separator, brou_rslt)
            file_content += line + "\n"

        # 2. Línea de cierre
        trailer = self._build_brou_trailer(payments, separator, brou_rslt)
        file_content += trailer + "\n"

        return {"file": file_content, "brou_rslt": brou_rslt}

    # ======================
    # DETALLE (una línea por pago)
    # ======================
    def _build_brou_line(self, payment, separator, brou_rslt):
        invoices = payment.invoice_ids
        invoice = invoices[0] if invoices else None
        config_l_vars = {line.sequence: line for line in self.line_ids}

        # Tipo de registro (Constante 1)
        d1_value = config_l_vars.get(1).value if config_l_vars.get(1) else "1"
        d1 = self._format_field_brou(d1_value, "d1")

        # Marca (espacio en blanco)
        d2_value = " "
        d2 = self._format_field_brou(d2_value, "d2")

        # Código de Banco (Constante 001)
        d3_value = config_l_vars.get(3).value if config_l_vars.get(3) else "001"
        d3 = self._format_field_brou(d3_value, "d3")

        # Filler (00)
        d4_value = "0"
        d4 = self._format_field_brou(d4_value, "d4", padding='0')

        # Fecha de vencimiento (AAMMDD)
        batch_date = (
            payment.batch_payment_id.date
            if payment and payment.batch_payment_id and payment.batch_payment_id.date
            else None
        )
        d5_value = batch_date.strftime('%y%m%d') if batch_date else ""
        d5 = self._format_field_brou(d5_value, "d5")

        # Referencia de servicio
        convenio = invoice.agreement_id.code if hasattr(invoice, 'agreement_id') else '0'
        matricula = invoice.commercial_registration if hasattr(invoice, 'commercial_registration') else '0'
        convenio = convenio.rjust(5, "0")
        matricula = matricula.rjust(10, "0")
        d6_value = f"{convenio}{matricula}"
        d6 = self._format_field_brou(d6_value, "d6", padding='0', just='left')

        # Convenio (suministrado por BROU)
        d7_value = config_l_vars.get(7).value if config_l_vars.get(7) else ""
        d7 = self._format_field_brou(d7_value, "d7", padding='0')

        # Moneda (98 = pesos, 01 = dólares)
        if config_l_vars.get(8) and config_l_vars.get(8).type == 'mapping':
            d8_value = self._get_mapped_value(
                config_l_vars.get(8),
                payment.currency_id.name,
                COLUMNS_TITLES_BROU_DETAIL['d8'],
                payment,
                brou_rslt
            )
        else:
            d8_value = config_l_vars.get(8).value if config_l_vars.get(8) else " "

        d8 = self._format_field_brou(d8_value, "d8")

        # Código de registro (Constante A)
        d9_value = config_l_vars.get(9).value if config_l_vars.get(9) else "A"
        d9 = self._format_field_brou(d9_value, "d9")

        # Filler (ceros)
        d10_value = "0"
        d10 = self._format_field_brou(d10_value, "d10", padding='0')

        # Fecha de producción (AAMM)
        d11_value = invoice.invoice_date.strftime('%y%m') if invoice and invoice.invoice_date else ""
        d11 = self._format_field_brou(d11_value, "d11")

        # Importe
        d12_value = f"{payment.amount:.2f}".replace('.', '')
        d12 = self._format_field_brou(d12_value, "d12", padding='0')

        # Filler (ceros)
        d13_value = "0"
        d13 = self._format_field_brou(d13_value, "d13", padding='0')

        # Información de la empresa
        d14_value = "%s%s" % (invoice.commercial_serie or "", invoice.commercial_number or "") if invoice else ""
        d14 = self._format_field_brou(d14_value, "d14", padding='0')

        # Identificador de factura
        d15_value = self.get_invoice_brou(invoice.name) if invoice else ""
        d15 = self._format_field_brou(d15_value, "d15", padding='0')

        # Consumidor final (1 = Sí, 0 = No)
        d16_val = "0"
        if invoice and invoice.l10n_latam_document_type_id and invoice.l10n_latam_document_type_id == self.env.ref('l10n_uy.dc_e_ticket'):
            d16_val = "1"

        d16_value = config_l_vars.get(16).value if config_l_vars.get(16) else d16_val
        d16 = self._format_field_brou(d16_value, "d16")

        # Importe gravado IVA básico
        iva_basico = sum(invoices.mapped('taxable_amount')) if invoices else 0.0
        d17_value = f"{iva_basico:.2f}".replace('.', '')
        d17 = self._format_field_brou(d17_value, "d17", padding='0')

        # Importe gravado IVA mínimo. No hay facturas con IVA Mínimo posibles de envío por débito.
        d18_value = "0"
        d18 = self._format_field_brou(d18_value, "d18", padding='0')

        # Importe devolución IVA (informado por BROU → se pone en ceros)
        d19_value = "0"
        d19 = self._format_field_brou(d19_value, "d19", padding='0')

        return separator.join([
            d1, d2, d3, d4, d5, d6, d7, d8, d9,
            d10, d11, d12, d13, d14, d15, d16,
            d17, d18, d19
        ])

    # ======================
    # TRAILER (línea de cierre)
    # ======================
    def _build_brou_trailer(self, payments, separator, brou_rslt):
        payment = payments[0] if payments else None
        config_t_vars = {line.sequence: line for line in self.footer_ids}

        total = sum(p.amount for p in payments)
        total_iva_minimo = 0.0
        invoices = payments.mapped('invoice_ids')
        total_iva_basico = sum(invoices.mapped('taxable_amount'))

        # Tipo de registro (Constante 2)
        t1_value = config_t_vars.get(1).value if config_t_vars.get(1) else "2"
        t1 = self._format_field_brou_trailer(t1_value, "t1")

        # Marca (espacio en blanco)
        t2_value = " "
        t2 = self._format_field_brou_trailer(t2_value, "t2")

        # Código de Banco (Constante 001)
        t3_value = config_t_vars.get(3).value if config_t_vars.get(3) else "001"
        t3 = self._format_field_brou_trailer(t3_value, "t3")

        # Filler (00)
        t4_value = "0"
        t4 = self._format_field_brou_trailer(t4_value, "t4", padding='0')

        # Fecha de vencimiento
        batch_date = (
            payment.batch_payment_id.date
            if payment and payment.batch_payment_id and payment.batch_payment_id.date
            else None
        )
        t5_value = batch_date.strftime('%y%m%d') if batch_date else ""
        t5 = self._format_field_brou_trailer(t5_value, "t5")

        # Facturas a debitar
        t6_value = str(len(payments))
        t6 = self._format_field_brou_trailer(t6_value, "t6", padding='0')

        # Importe total a debitar
        t7_value = f"{total:.2f}".replace('.', '')
        t7 = self._format_field_brou_trailer(t7_value, "t7", padding='0')

        # Cantidad de facturas (Constante ceros)
        t8_value = "0"
        t8 = self._format_field_brou_trailer(t8_value, "t8", padding='0')

        # Importe total debitado (Constante ceros)
        t9_value = "0"
        t9 = self._format_field_brou_trailer(t9_value, "t9", padding='0')

        # Facturas no debitadas (Constante ceros)
        t10_value = "0"
        t10 = self._format_field_brou_trailer(t10_value, "t10", padding='0')

        # Importe total no debitado (Constante ceros)
        t11_value = "0"
        t11 = self._format_field_brou_trailer(t11_value, "t11", padding='0')

        # Total comisiones BROU (Constante ceros)
        t12_value = "0"
        t12 = self._format_field_brou_trailer(t12_value, "t12", padding='0')

        # IVA (Constante ceros)
        t13_value = "0"
        t13 = self._format_field_brou_trailer(t13_value, "t13", padding='0')

        # Información empresa
        t14_value = config_t_vars.get(14).value if config_t_vars.get(14) else ' '
        t14 = self._format_field_brou_trailer(t14_value, "t14", padding='0')

        # Importe total gravado IVA básico
        t15_value = f"{total_iva_basico:.2f}".replace('.', '')
        t15 = self._format_field_brou_trailer(t15_value, "t15", padding='0')

        # Importe total gravado IVA mínimo
        t16_value = f"{total_iva_minimo:.2f}".replace('.', '')
        t16 = self._format_field_brou_trailer(t16_value, "t16", padding='0')

        # Importe devolución de IVA (Constante ceros)
        t17_value = "0"
        t17 = self._format_field_brou_trailer(t17_value, "t17", padding='0')

        # Filler (ceros)
        t18_value = "0"
        t18 = self._format_field_brou_trailer(t18_value, "t18", padding='0')

        return separator.join([
            t1, t2, t3, t4, t5, t6, t7, t8, t9,
            t10, t11, t12, t13, t14, t15, t16, t17, t18
        ])

    # ======================
    # UTILIDADES
    # ======================
    def _format_field_brou_trailer(self, value, field_name, padding=' ', just='right'):
        return self._format_field_brou(value, field_name, padding, just, 'trailer')

    def _format_field_brou(self, value, field_name, padding=' ', just='right', env_context='line'):
        contexts = {
            'line': EXPECTED_LENGTHS_BROU_DETAIL,
            'trailer': EXPECTED_LENGTHS_BROU_TRAILER,
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

    def get_invoice_brou(self, invoice_number_str):
        # Tomar solo la última parte del string
        clean_str = invoice_number_str.strip().split()[-1]
        return clean_str
