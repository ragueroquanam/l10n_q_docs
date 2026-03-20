from odoo import api, fields, models, _


class AccountBatchPaymentCheckConfirmationWizard(models.TransientModel):
    _name = 'account.batch.payment.check.confirmation.wizard'
    _description = 'Confirmacion de comprobacion de lote de pagos'

    batch_id = fields.Many2one('account.batch.payment', required=True, readonly=True)
    expected_count = fields.Integer(string='Cantidad esperada', readonly=True)
    current_count = fields.Integer(string='Cantidad actual', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        batch = self.env['account.batch.payment'].browse(self.env.context.get('default_batch_id'))
        if batch:
            res.update({
                'batch_id': batch.id,
                'expected_count': batch.payment_queue_count,
                'current_count': len(batch.payment_ids),
            })
        return res

    def action_confirm(self):
        self.ensure_one()
        self.batch_id.with_context(force_check=True).write({'is_checked': True})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
