from odoo import models, fields, api, _
from lxml.builder import E


class BaseWizard(models.TransientModel):
    _inherit = "base.wizard"

    def action_confirm(self):
        result = super(BaseWizard, self).action_confirm()
        if result.get("type") == "ir.actions.act_window_close" and self._context.get("source_session_id"):
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'cash.management.session',
                'res_id': self._context.get("source_session_id"),
                'view_mode': 'form',
                'target': 'current',
            }
        return result
