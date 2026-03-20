# -*- coding: utf-8 -*-

import requests
import json
import logging
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RestAPIClient:
    def __init__(self, provider, env, timeout=15):
        self.provider = provider  # instancia de pos.payment.provider
        self.timeout = timeout
        self.env = env
        self.headers = {'Content-Type': 'application/json'}

    def post(self, service, data=None, logger=False):
        return self._request('POST', service, data, logger)

    def get(self, service, params=None, logger=False):
        return self._request('GET', service, params, logger)

    def _request(self, method, service, data=None, logger=False):
        url = f"{self.provider.base_url.rstrip('/')}/{self.provider.endpoint.lstrip('/')}/{service}"
        body = json.dumps(data or {})

        # Crear el log inicial con ORM
        log = self.provider.env['pos.transaction.log'].sudo().create({
            'method': method,
            'endpoint': url,
            'request_body': body,
            'payment_provider_id': self.provider.id,
            'state': 'sent',
        })
        self.env.cr.commit()

        if logger:
            _logger.debug({
                'method': method,
                'endpoint': url,
                'request_body': body,
                'payment_provider_id': self.provider.id,
                'state': 'sent',
            })

        try:
            _logger.info(f"[POS] {method} {url} | Data: {body}")
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                data=body if method in ['POST', 'PUT'] else None,
                timeout=self.timeout
            )
            response.raise_for_status()

            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text

            log.sudo().write({
                'response_body': json.dumps(response_data, indent=2) if isinstance(response_data, dict) else str(
                    response_data),
                'state': 'success',
            })
            self.env.cr.commit()
            if logger:
                _logger.debug(
                    json.dumps(response_data, indent=2) if isinstance(response_data, dict) else str(response_data))

            return response_data

        except requests.RequestException as e:
            log.sudo().write({
                'response_body': str(e),
                'state': 'failed',
            })
            _logger.error(f"Error al consumir el servicio POS: {e}")
            raise UserError(_("Error de conexión con el proveedor de pago:\n%s" % e))
