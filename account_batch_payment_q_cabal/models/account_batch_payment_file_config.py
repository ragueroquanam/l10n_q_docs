# -*- coding: utf-8 -*-

from odoo import models, fields, _

# Longitudes esperadas para cada campo del archivo CABAL
EXPECTED_LENGTHS_CABAL = {
    'd1': 4,  # "CBCU" constante
    'd2': 11,  # Número de comercio
    'd3': 1,  # Código de moneda (N=Pesos, U=Dólares)
    'd4': 16,  # Número de tarjeta
    'd5': 9,  # Número de socio en la institución
    'd6': 11,  # Importe a debitar (con 2 decimales implícitos)
    'd7': 6,  # Fecha de proceso DDMMAA
    'd8': 4,  # Número de cuota MMAA
    'd9': 12,  # Identificación de factura
    'd10': 1,  # Aplica devolución de IVA (1=Sí, 0=No)
    'd11': 15,  # Importe gravado básico (con 2 decimales implícitos)
    'd12': 15,  # Importe gravado mínimo (con 2 decimales implícitos)
    'd13': 15,  # Importe devolución de IVA (con 2 decimales implícitos)
    'd14': 8,  # Filler
}

COLUMNS_TITLES_CABAL = {
    'd1': 'Constante CBCU',
    'd2': 'Número de comercio',
    'd3': 'Código de moneda',
    'd4': 'Número de tarjeta',
    'd5': 'Número de socio institución',
    'd6': 'Importe a debitar',
    'd7': 'Fecha de proceso',
    'd8': 'Número de cuota',
    'd9': 'Identificación de factura',
    'd10': 'Aplica devolución IVA',
    'd11': 'Importe gravado básico',
    'd12': 'Importe gravado mínimo',
    'd13': 'Importe devolución IVA',
    'd14': 'Filler',
}


class AccountBatchPaymentFileConfig(models.Model):
    _inherit = "account.bank.payment.file.config"

    def check_payments_for_errors(self, payments):
        """ Valida los pagos para el formato CABAL.
        Params:
            payments: Lista de pagos a procesar.
        """
        rslt = super(AccountBatchPaymentFileConfig, self).check_payments_for_errors(payments)

        if self.code in ('cabal_pmsa', 'cabal_cmsa'):
            cabal_rslt = []

            # Variables requeridas en líneas: 1 (Constante CBCU), 2 (comercio), 3 (moneda), 10 (aplica IVA)
            config_l_vars = {line.sequence: line for line in self.line_ids}
            missing_keys = [k for k in [1, 2, 3, 10] if k not in config_l_vars]
            for k in missing_keys:
                cabal_rslt.append({
                    'title': _("La variable %s no está configurada en las líneas del archivo de pago CABAL.") % k,
                    'records': payments,
                    'help': ''
                })

            values = self._get_values_cabal(payments)
            cabal_rslt.extend(values.get('cabal_rslt', []))
            rslt.extend(cabal_rslt)

        return rslt

    def _generate_payment_file_cabal_pmsa(self, payments):
        """Genera el archivo de pago en formato CABAL para PMSA."""
        return self._get_values_cabal(payments).get('file', '')

    def _generate_payment_file_cabal_cmsa(self, payments):
        """Genera el archivo de pago en formato CABAL para CMSA."""
        return self._get_values_cabal(payments).get('file', '')

    def _get_values_cabal(self, payments):
        """
        Genera el archivo CABAL con estructura:
        - Solo líneas de detalle (una por cada payment)
        - Sin encabezado ni línea de cierre
        """
        cabal_rslt = []
        file_content = ""
        separator = self.column_separator or ''

        # Líneas de detalle
        for payment in payments:
            line = self._build_cabal_line(payment, separator, cabal_rslt)
            file_content += line + "\n"

        return {"file": file_content, "cabal_rslt": cabal_rslt}

    def _build_cabal_line(self, payment, separator, cabal_rslt):
        """Construye una línea del archivo CABAL para un pago."""
        invoice_ids = getattr(payment, "invoice_ids", None)
        invoice = invoice_ids[0] if invoice_ids else None
        config_l_vars = {line.sequence: line for line in self.line_ids}

        # d1: Constante "CBCU"
        d1_value = config_l_vars.get(1).value if config_l_vars.get(1) else ""
        d1 = self._format_field_cabal(d1_value, "d1")

        # d2: Número de comercio (configurable por empresa)
        d2_value = config_l_vars.get(2).value if config_l_vars.get(2) else ""
        d2 = self._format_field_cabal(d2_value, "d2", padding='0')

        # d3: Código de moneda (N=Pesos, U=Dólares)
        if config_l_vars.get(3) and config_l_vars.get(3).type == 'mapping':
            d3_value = self._get_mapped_value(
                config_l_vars.get(3),
                payment.currency_id.name,
                COLUMNS_TITLES_CABAL['d3'],
                payment,
                cabal_rslt
            )
        else:
            d3_value = config_l_vars.get(3).value if config_l_vars.get(3) else "N"
        d3 = self._format_field_cabal(d3_value, "d3")

        # d4: Número de tarjeta
        card_info_dict = self._get_card_info(payment)
        num_tarj = str(card_info_dict.get('card_number') or '').strip()
        if not num_tarj:
            cabal_rslt.append({
                'title': _("El pago %s no tiene número de tarjeta configurado en el afiliado.") % payment.name,
                'records': payment,
                'help': ''
            })
        d4 = self._format_field_cabal(num_tarj, "d4", padding='0')

        # d5: Número de socio en la institución
        # PMSA: commercial_registration (Matrícula/Módulo)
        # CMSA: current_account (Contrato)
        if self.code == 'cabal_pmsa':
            d5_value = invoice.commercial_registration if invoice and hasattr(invoice,
                                                                              'commercial_registration') else ''
        else:  # cabal_cmsa
            d5_value = invoice.current_account if invoice and hasattr(invoice, 'current_account') else ''

        # if not d5_value:
        #     cabal_rslt.append({
        #         'title': _("El pago %s no tiene número de socio institución configurado.") % payment.name,
        #         'records': payment,
        #         'help': ''
        #     })
        d5 = self._format_field_cabal(d5_value, "d5", padding=' ')

        # d6: Importe a debitar (monto factura IVA incluido, sin separador decimal)
        amount_value = payment.amount or 0.0
        d6_value = f"{amount_value:.2f}".replace(".", "")
        d6 = self._format_field_cabal(d6_value, "d6", padding='0')

        # d7: Fecha de proceso DDMMAA (fecha creación archivo = fecha del batch)
        batch_date = (
            payment.batch_payment_id.date
            if payment.batch_payment_id and payment.batch_payment_id.date
            else payment.date
        )
        d7_value = batch_date.strftime("%d%m%y") if batch_date else ""
        d7 = self._format_field_cabal(d7_value, "d7", padding='0')

        # d8: Número de cuota MMAA
        # PMSA: Mes de cargo (campo Fecha de entrega en Odoo -> delivery_date)
        # CMSA: Mes/Año de la fecha de factura (invoice_date)
        if self.code == 'cabal_pmsa':
            # Usar delivery_date de la factura
            fee_date = invoice.delivery_date if invoice and hasattr(invoice,
                                                                    'delivery_date') and invoice.delivery_date else None
            if not fee_date:
                # Fallback a invoice_date si no hay delivery_date
                fee_date = invoice.invoice_date if invoice else None
        else:  # cabal_cmsa
            fee_date = invoice.invoice_date if invoice else None

        d8_value = fee_date.strftime("%m%y") if fee_date else ""
        d8 = self._format_field_cabal(d8_value, "d8", padding='0')

        # d9: Identificación de factura (11 caracteres)
        d9_value = self._get_invoice_cabal(invoice.name if invoice else '')
        d9 = self._format_field_cabal(d9_value, "d9")

        # d10: Aplica devolución de IVA (1=Sí, 0=No)
        if config_l_vars.get(10) and config_l_vars.get(10).type == 'mapping':
            aplica = getattr(payment, 'vat_refund_applicable', None)
            aplica_odoo = 'true' if aplica else 'false' if aplica is not None else ''
            d10_value = self._get_mapped_value(
                config_l_vars.get(10),
                aplica_odoo,
                COLUMNS_TITLES_CABAL['d10'],
                payment,
                cabal_rslt
            )
        else:
            d10_value = config_l_vars.get(10).value if config_l_vars.get(10) else '0'
        d10 = self._format_field_cabal(d10_value, "d10", padding='0')

        # d11: Importe gravado básico (sin separador decimal)
        gravado_basico = sum(invoice_ids.mapped('taxable_amount')) if invoice_ids else 0.0
        d11_value = f"{gravado_basico:.2f}".replace(".", "")
        d11 = self._format_field_cabal(d11_value, "d11", padding='0')

        # d12: Importe gravado mínimo (sin separador decimal)
        # Por ahora se establece en 0
        gravado_minimo = 0.0
        d12_value = f"{gravado_minimo:.2f}".replace(".", "")
        d12 = self._format_field_cabal(d12_value, "d12", padding='0')

        # d13: Importe devolución de IVA (sin separador decimal)
        # Por ahora se establece en 0
        devolucion_iva = 0.0
        d13_value = f"{devolucion_iva:.2f}".replace(".", "")
        d13 = self._format_field_cabal(d13_value, "d13", padding='0')

        # d14: Filler (espacios)
        d14 = self._format_field_cabal("", "d14")

        return separator.join([
            d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11, d12, d13, d14
        ])

    def _format_field_cabal(self, value, field_name, padding=' ', just='right'):
        """
        Formatea un campo para el archivo CABAL según la longitud esperada.
        
        Args:
            value: Valor a formatear
            field_name: Nombre del campo (d1, d2, etc.)
            padding: Carácter de relleno (por defecto espacio)
            just: Justificación ('right' o 'left')
        
        Returns:
            Cadena formateada a la longitud correcta
        """
        length = EXPECTED_LENGTHS_CABAL.get(field_name, 0)

        if not padding or len(padding) != 1:
            padding = ' '

        value_str = str(value)[:length] if value else ''

        if just == 'right':
            return value_str.rjust(length, padding)
        else:
            return value_str.ljust(length, padding)

    def _get_invoice_cabal(self, invoice_number_str):
        """
        Extrae el número de factura limpio para el archivo CABAL.
        
        Args:
            invoice_number_str: Nombre/número de la factura
        
        Returns:
            Número de factura limpio (máximo 12 caracteres)
        """
        if not invoice_number_str:
            return ''

        # Tomar solo la última parte del string (después del último espacio)
        clean_str = invoice_number_str.strip().split()[-1]

        # Eliminar caracteres no alfanuméricos excepto guiones
        clean_str = ''.join(c for c in clean_str if c.isalnum() or c == '-')

        return clean_str[:12] if clean_str else ''
