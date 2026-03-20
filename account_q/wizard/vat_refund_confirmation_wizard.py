from odoo import models


class VatRefundConfirmationWizard(models.TransientModel):
    _name = 'vat.refund.confirmation.wizard'
    _description = 'Confirmar omisión de devolución de IVA'

    def action_confirm_skip(self):
        # Buscar el wizard account.payment.register activo
        register = self.env['account.payment.register'].browse(self.env.context.get('active_id'))
        if not register:
            return

        # Ejecutar action_create_payments con el contexto forzado
        return register.with_context(force_skip_vat_refund_check=True).action_create_payments()


class VatRefundConfirmationMultiWizard(models.TransientModel):
    _name = 'vat.refund.confirmation.multi.wizard'
    _description = 'Confirmar omisión de devolución de IVA'

    def action_confirm_skip(self):
        # Buscar el wizard account.payment.register activo
        register = self.env['multi.invoice.payment.wizard'].browse(self.env.context.get('multi_invoice_payment_id'))
        if not register:
            return

        # Ejecutar action_create_payments con el contexto forzado
        n_context = dict(self.env.context)
        n_context['force_skip_vat_refund_check'] = True
        # _new_context.update({
        #     'active_ids': self.ids,
        #     'active_model': 'account.move',
        #     'default_invoice_currency_id': currencies[0].id if currencies else False,
        #     'default_invoice_ids': [(6, 0, self.ids)],
        #     'default_move_type': self[0].move_type,
        #     'default_company_id': companies[0].id
        # })
        return register.with_context(n_context).action_generate_payments()