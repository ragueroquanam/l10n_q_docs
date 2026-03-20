# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models, api, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_validate_multi(self):
        if self.filtered(lambda x: x.state != 'in_process' or x.move_id):
            raise ValidationError(_("Solo puedes validar Pagos en Lote si están en estado 'En Proceso' "
                                    "y no tienen un movimiento asociado."))
        return super(AccountPayment, self).action_validate()

    def action_reject_multi(self):
        if self.filtered(lambda x: x.state != 'in_process' or not x.is_sent):
            raise ValidationError(_("Solo puedes rechazar Pagos en Lote si están en estado 'En Proceso' "
                                    "y no han sido enviados."))
        self.action_reject()

    def action_reject(self):
        self.action_cancel()
        return super(AccountPayment, self).action_reject()


    def unmark_as_sent(self):
        self.batch_payment_id = False
        return super(AccountPayment, self).unmark_as_sent()

    @api.model
    def _get_method_codes_using_bank_account(self):
        codes = super(AccountPayment, self)._get_method_codes_using_bank_account()
        codes.append('batch_payment')
        return codes

    def message_post(self, **kwargs):
        """
        """
        self.ensure_one()
        match = re.search(r"data-oe-id=['\"](\d+)['\"]", str(kwargs.get('body', '')))
        if match:
            linked_batch_id = int(match.group(1))
        else:
            linked_batch_id = False
        cond1 = 'removed' in kwargs.get('body', '') or 'Pago eliminado' in kwargs.get('body', '')
        cond2 = linked_batch_id and self.batch_payment_id and self.batch_payment_id.id == linked_batch_id
        if cond1 and cond2:
            return False
        return super().message_post(**kwargs)
