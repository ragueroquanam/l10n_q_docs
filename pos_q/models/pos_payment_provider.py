# -*- coding: utf-8 -*-

import base64

from odoo import models, fields, tools
from .rest_api_client import RestAPIClient


class PosPaymentProvider(models.Model):
    _name = 'pos.payment.provider'
    _description = 'Proveedor de Pago POS'
    _order = 'name'

    def _get_default_image(self):
        default_image_path = 'pos_q/static/src/img/box.png'
        return base64.b64encode(tools.misc.file_open(default_image_path, 'rb').read())

    code = fields.Char(string='Código', required=True)
    name = fields.Char(string='Nombre', required=True)
    base_url = fields.Char(string='URL', required=True)
    endpoint = fields.Char(string='Dirección del servicio', required=True)
    system_id = fields.Char(string='Identificador del sistema', required=False)
    logo = fields.Binary(string='Logotipo', attachment=True, default=_get_default_image)
    active = fields.Boolean(string='Activo', default=True)
    terminal_ids = fields.One2many(
        comodel_name='pos.payment.terminal',
        inverse_name='provider_id',
        string='Terminales de Pago'
    )

    def send_pos_request(self, service, data):
        """
        Método auxiliar para enviar una petición usando el cliente REST genérico
        """
        self.ensure_one()
        client = RestAPIClient(provider=self, env=self.env)
        return client.post(service, data, True)

    def _format_amount_for_pos(self, amount):
        if amount is None:
            return "0"
        return str(int(round(amount * 100)))
