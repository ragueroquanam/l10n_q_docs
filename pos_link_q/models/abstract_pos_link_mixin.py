# -*- coding: utf-8 -*-

import logging
import time
from datetime import datetime
from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RESPONSE_CODES = {
    0: "Resultado OK",
    100: "Número de pinpad inválido",
    101: "Número de sucursal inválido",
    102: "Número de caja inválido",
    103: "Fecha de la transacción inválida",
    104: "Monto no válido",
    105: "Cantidad de cuotas inválidas",
    106: "Número de plan inválido",
    107: "Número de factura inválido",
    108: "Moneda ingresada no válida",
    109: "Número de ticket inválido",
    110: "No existe transacción",
    111: "Transacción finalizada",
    112: "Identificador de sistema inválido",
    113: "Se debe consultar por la transacción",
    10: "Aguardando por operación en el pinpad",
    11: "Tiempo de transacción excedido, envíe datos nuevamente",
    12: "Pinpad consultó datos (se pasó la tarjeta o Poleo Automático)",
    999: "Error no determinado",
    -100: "Formato en campo/s incorrecta; Faltan campos obligatorios",
}

POS_RESPONSE_CODES = {
    "00": "Aprobado.",
    "01": "Contacte al emisor, en caso de ser aprobada realizar operación offline.",
    "02": "Idem al anterior.",
    "03": "Comercio inválido.",
    "04": "Retener tarjeta.",
    "05": "Transacción negada.",
    "06": "Error (utilizado en transferencia de archivos).",
    "07": "Retenga y llame.",
    "08": "Aprobado EMV (Mastercard).",
    "10": "Aprobado Parcialmente (CashBack).",
    "11": "Aprobado (igual que 00).",
    "12": "Transacción inválida.",
    "13": "Monto inválido.",
    "14": "Tarjeta inválida o cédula no corresponde con titular.",
    "15": "Emisor no valido.",
    "21": "No se tomó acción (reversas y anulaciones).",
    "25": "No existe original, registro no encontrado en archivo de transacciones.",
    "30": "Error en formato del mensaje.",
    "31": "Tarjeta no soportada.",
    "38": "Denegada, excede cantidad de reintentos de PIN permitida.",
    "41": "Tarjeta perdida, retener.",
    "43": "Tarjeta robada, retener.",
    "45": "Tarjeta inhabilitada para operar en cuotas.",
    "46": "Tarjeta no vigente.",
    "47": "PIN requerido.",
    "48": "Excede cantidad máxima de cuotas permitidas.",
    "49": "Error en formato de fecha de expiración.",
    "50": "Monto ingresado en entrega supera limite.",
    "51": "Sin disponible.",
    "53": "Cuenta inexistente.",
    "54": "Tarjeta vencida.",
    "55": "PIN incorrecto.",
    "56": "Emisor no habilitado en el sistema.",
    "57": "Transacción no permitida a esta tarjeta.",
    "58": "Servicio inválido. Transacción no permitida a la terminal.",
    "59": "Sospecha de fraude.",
    "61": "Excede monto límite de actividad - Contacte al emisor.",
    "62": "Tarjeta restringida para dicha terminal u operacion.",
    "65": "Límite de actividad excedido - Contacte al emisor.",
    "76": "Solicitar autorización telefónica, en caso de ser aprobada, cargar el código obtenido y dejar operación en offline.",
    "77": "Error en plan/cuotas.",
    "78": "Debe cambiar Pin",
    "81": "Error criptográfico en manejo de pin online.",
    "82": "Error en validación de CVV.",
    "83": "Imposible verificar PIN en manejo de pin online.",
    "84": "Moneda Invalida.",
    "85": "Aprobado.",
    "89": "Terminal inválida.",
    "91": "Emisor no responde.",
    "94": "Número de secuencia duplicado, repita e incremente en uno systemtrace.",
    "95": "Diferencia en el cierre de transacciones, inicie Batch Upload.",
    "96": "Error de sistema.",
    "98": "Mensajes Especiales.",
    "CE": "Error en conexión al Host.",
    "CF": "Consulta Caja Fallido.",
    "CT": "Cancelar Transacción.",
    "EA": "Error en código de comercio.",
    "EB": "Error en Batch (Lote).",
    "EC": "Error en Cierre de lote.",
    "EE": "Error Rutinas EMV.",
    "EI": "Error en Información enviada al PinPad.",
    "ER": "Error enviando Reverso al Autorizador.",
    "ET": "Error en Ingreso Inicial de Datos.",
    "LL": "Lote Lleno.",
    "LV": "Lote Vacío.",
    "MK": "MasterKey Ausente.",
    "N7": "CVV2 no válido.",
    "NC": "No responde Caja a Mensaje Inicial.",
    "NP": "Operación NO Permitida.",
    "NR": "No responde Autorizador.",
    "OF": "Aprobación Offline.",
    "TI": "Tarjeta incorrecta.",
    "TN": "Tarjeta Incorrecta en Offline (ùltimos N dígitos).",
    "TP": "Transacción Pendiente (usado por billeteras)",
    "TO": "TimeOut Ingreso Tarjeta.",
    "XX": "Cualquier otro código no especificado, denegada."
}


class AbstractPosLinkMixin(models.AbstractModel):
    _name = "abstract.pos.link.mixin"
    _description = "Mixin for POS Link provider"

    log_pos_transactions = False

    def _prepare_pos_request_basic_data(self, provider, terminal, other_data=None):
        other_data = other_data or {}

        if not terminal.pos_id:
            raise UserError(_("El terminal POS no tiene asignado un número de terminal (PosID)."))
        if not provider.system_id:
            raise UserError(_("El proveedor de pago no tiene asignado un SystemId."))
        if not terminal.branch:
            raise UserError(_("El terminal POS no tiene asignado un identificador de sucursal (Branch)."))
        if not terminal.client_app_id:
            raise UserError(_("El terminal POS no tiene asignado un identificador de caja (ClientAppId)."))

        return {
            "PosID": terminal.pos_id,
            "SystemId": provider.system_id,
            "Branch": terminal.branch,
            "ClientAppId": terminal.client_app_id,
            "UserId": str(self.env.uid),
            "TransactionDateTimeyyyyMMddHHmmssSSS": datetime.now().strftime('%Y%m%d%H%M%S%f')[:17],
            **other_data
        }

    def reverse_last_pending_transaction(self, provider, terminal):
        """Revierte la última transacción pendiente (sin respuesta) de un terminal."""
        transaction = self.env['pos.transaction'].sudo().search([
            ('pos_payment_terminal_id', '=', terminal.id),
            ('got_response', '=', False),
            ('is_reversed', '=', False)
        ], order='transaction_date desc', limit=1)

        if transaction:
            transaction_number = transaction.transaction_number
            rev_data = self._prepare_pos_request_processFinancialReverse(provider, terminal, transaction_number)
            query_response, query_code = self._execute_pos_transaction(provider, "processFinancialReverse",
                                                                       rev_data, success_codes=[0])
            if query_code == 0:
                _logger.info("Transacción revertida exitosamente para terminal %s, transacción %s",
                             terminal.display_name, transaction_number)
                transaction.is_reversed = True
                self.env.cr.commit()

    def _get_response_message(self, code):
        return RESPONSE_CODES.get(code, f"Código de error desconocido: {code}")

    def _get_pos_response_message(self, code):
        return POS_RESPONSE_CODES.get(code, f"Error en el pos {code}")

    def _execute_pos_transaction(self, provider, operation, request_data, success_codes=[0, 10, 12]):
        """
        Ejecuta una transacción POS y maneja los errores por código de respuesta.
        """
        if self.log_pos_transactions:
            _logger.info("Inicio Transacción POS [%s]: datos solicitud=%s", operation, request_data)
        response = provider.send_pos_request(operation, request_data)
        response_code = int(response.get('ResponseCode', -1))
        if self.log_pos_transactions:
            _logger.info("Resultado transacción POS [%s]: código=%s, respuesta=%s", operation, response_code, response)
        if response_code not in success_codes:
            raise UserError(
                _("Error en la transacción '%s': %s") % (operation, self._get_response_message(response_code)))
        return response, response_code

    def _pos_transaction_loop_until_final_state(self, provider, terminal, request_data, operation, success_codes=[0],
                                                code_return=-1):
        # self.reverse_last_pending_transaction(provider, terminal)
        request_response, response_code = self._execute_pos_transaction(provider, operation, request_data,
                                                                        success_codes=success_codes)
        transaction_number = request_response.get('STransactionId', '')
        if response_code == code_return:
            return transaction_number, response_code, request_response, False

        operation_dict = {'processFinancialPurchaseVoidByTicket': 'cancel',
                          'processFinancialPurchase': 'sale',
                          'processFinancialPurchaseRefund': 'refund',
                          }
        transaction_obj = None
        if transaction_number:
            transaction_obj = self.env['pos.transaction'].sudo().create({
                'transaction_number': transaction_number,
                'pos_payment_terminal_id': terminal.id,
                'operation_type': operation_dict.get(operation, 'sale'),
                'request_data': request_data,
                'got_response': False,
                'response_text': '',
            })
            self.env.cr.commit()

        query_code = 10
        query_response = {}
        process_reverse = False
        while query_code in [10, 12]:
            time.sleep(3)
            query_data = self._prepare_pos_request_processFinancialPurchaseQuery(provider, terminal, transaction_number)
            query_response, query_code = self._execute_pos_transaction(provider, "processFinancialPurchaseQuery",
                                                                       query_data)

            RemainingExpirationTime = query_response.get('RemainingExpirationTime', -1)
            PosResponseCode = query_response.get('PosResponseCode', "")
            if query_code == 0 and RemainingExpirationTime == 0 and PosResponseCode != "00":
                if transaction_obj:
                    transaction_obj.sudo().write({'got_response': True, 'response_text': query_response})
                    self.env.cr.commit()
                raise UserError(
                    _("Error en la transacción: %s") % (self._get_pos_response_message(PosResponseCode)))

            if query_code in [12] and RemainingExpirationTime == 0:
                rev_data = self._prepare_pos_request_processFinancialReverse(provider, terminal, transaction_number)
                query_response, query_code = self._execute_pos_transaction(provider, "processFinancialReverse",
                                                                           rev_data)
                process_reverse = True

        if query_code == 0:
            transaction_obj.sudo().write({'got_response': True, 'response_text': query_response})
            self.env.cr.commit()

        if process_reverse:
            raise UserError(_("No se realizó el pago. El proceso fue revertido automáticamente."))
        if not transaction_number:
            raise UserError(_("No se pudo obtener el número de transacción del proveedor POS."))
        if not query_response:
            raise UserError(_("No se obtuvo respuesta del proveedor POS."))

        return transaction_number, query_code, query_response, process_reverse

    # Consulta el estado de una transacción previamente inicializada
    def _prepare_pos_request_processFinancialPurchaseQuery(self, provider, terminal, transaction_number):
        basic_data = self._prepare_pos_request_basic_data(provider, terminal)
        if not basic_data:
            return {}
        return {
            **basic_data,
            "TransactionId": int(transaction_number),
            "StransactionId": transaction_number
        }

    # Cancelacion de compra
    def _prepare_pos_request_cancelFinancialPurchase(self, provider, terminal, transaction_number):
        basic_data = self._prepare_pos_request_basic_data(provider, terminal)
        if not basic_data:
            return {}
        return {
            **basic_data,
            "TransactionId": int(transaction_number),
            "StransactionId": transaction_number
        }

    # Reverso de compra
    def _prepare_pos_request_processFinancialReverse(self, provider, terminal, transaction_number):
        basic_data = self._prepare_pos_request_basic_data(provider, terminal)
        if not basic_data:
            return {}
        other_data = {
            "TransactionId": transaction_number
        }
        return {**basic_data, **other_data}

    # Anulacion de compra por ticket
    def _prepare_pos_request_processFinancialPurchaseVoidByTicket(self, provider, terminal, other_data):
        basic_data = self._prepare_pos_request_basic_data(provider, terminal)
        if not basic_data:
            return {}
        return {**basic_data, **other_data}

    # Devolucion de compra por ticket
    def _prepare_pos_request_processFinancialPurchaseRefund(self, provider, terminal, other_data):
        basic_data = self._prepare_pos_request_basic_data(provider, terminal)
        if not basic_data:
            return {}
        return {**basic_data, **other_data}

    # Obtener todas las transacciones del lote actual del POS.
    def _prepare_pos_request_processCurrentTransactionsBatchQuery(self, provider, terminal):
        basic_data = self._prepare_pos_request_basic_data(provider, terminal)
        if not basic_data:
            return {}
        return basic_data

    # Obtener todas las transacciones por fecha del POS.
    def _prepare_pos_request_BatchQuery(self, provider, terminal, other_data):
        basic_data = self._prepare_pos_request_basic_data(provider, terminal)
        if not basic_data:
            return {}
        return {**basic_data, **other_data}