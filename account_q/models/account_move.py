import re
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    taxable_amount = fields.Monetary(
        compute='_compute_taxable_amount', 
        string='Monto Gravable',
        currency_field='currency_id', 
        store=True
    )

    @api.depends('invoice_line_ids', 'invoice_line_ids.price_subtotal', 'invoice_line_ids.tax_ids')
    def _compute_taxable_amount(self):
        for rec in self:
            company = rec.company_id or self.env.company
            config_tax_ids = company.account_q_taxable_tax_ids.ids
            # Filtrar líneas que tienen al menos un impuesto en los impuestos configurados
            filtered_lines = rec.invoice_line_ids.filtered(
                lambda line: any(tax.id in config_tax_ids for tax in line.tax_ids)
            )
            rec.taxable_amount = sum(filtered_lines.mapped('price_subtotal'))

    @api.depends('name', 'ref')
    def _compute_l10n_latam_document_number(self):
        super(AccountMove, self)._compute_l10n_latam_document_number()

        # 2) Completa sólo donde no quedó valor y existe ref
        for rec in self.filtered(lambda r: not r.l10n_latam_document_number and r.ref):
            # Busca algo tipo A0000589 dentro de ref
            match = re.search(r'\b([A-Z]\d{7,})\b', rec.ref)
            rec.l10n_latam_document_number = match.group(1) if match else False
            if not rec.name:
                rec.name = rec.l10n_latam_document_number

    @api.depends('l10n_latam_available_document_type_ids')
    def _compute_l10n_latam_document_type(self):
        super()._compute_l10n_latam_document_type()

        # Lógica extendida: completar tipo de documento en facturas proveedor intercompany
        for rec in self.filtered(lambda x: x.move_type == 'in_invoice' and x.ref):
            source_invoice = self.env['account.move'].sudo().search([
                ('move_type', '=', 'out_invoice'),
                ('name', 'ilike', rec.ref)
            ], limit=1)

            if source_invoice and source_invoice.l10n_latam_document_type_id:
                rec.l10n_latam_document_type_id = source_invoice.l10n_latam_document_type_id.id

    @api.onchange('currency_id')
    def _onchange_currency_id_recompute_lines(self):
        for move in self:
            for line in move.line_ids:
                line._compute_account_id()

    @api.onchange('partner_id', 'currency_id')
    def _onchange_partner_id_topartner_bank_id(self):
        if self.move_type == 'in_invoice' and self.partner_id and self.currency_id:
            partner_bank = self.partner_id.bank_ids.filtered(lambda x: x.currency_id == self.currency_id)
            if partner_bank:
                partner_bank = partner_bank[0]
            self.partner_bank_id = partner_bank.id

    def _autopost_draft_entries(self, limit=100):
        ''' This method is called from a cron job.
        It is used to post entries such as those created by the module
        account_asset and recurring entries created in _post().
        '''
        moves = self.search([
            ('state', '=', 'draft'),
            ('date', '<=', fields.Date.context_today(self)),
            ('auto_post', '!=', 'no'),
            '|', ('checked', '=', True), ('journal_id.autocheck_on_post', '=', True)
        ], limit=limit)

        try:  # try posting in batch
            with self.env.cr.savepoint():
                moves._post()
        except UserError:  # if at least one move cannot be posted, handle moves one by one
            for move in moves:
                try:
                    with self.env.cr.savepoint():
                        move._post()
                except UserError as e:
                    move.checked = False
                    msg = _('The move could not be posted for the following reason: %(error_message)s', error_message=e)
                    move.message_post(body=msg, message_type='comment')

        if len(moves):
            self.env.ref('account.ir_cron_auto_post_draft_entry')._trigger()

    def action_toggle_block_payment_multi(self):
        # Validar si hay alguna factura con pago
        paid_moves = self.filtered(lambda move: move.payment_state in ('paid', 'in_payment'))
        if paid_moves:
            raise UserError(_(
                "No se puede realizar la operación de bloqueo porque al menos una de las facturas "
                "seleccionadas ya tiene pagos registrados.\n\n"
                "Por favor, revisa la selección y asegúrate de que todas las facturas estén sin pagos "
                "asociados antes de intentar bloquearlas."
            ))

        # Aplicar toggle a todas las demás
        for rec in self:
            rec.action_toggle_block_payment()

    def action_force_register_payment(self):
        if any(move.payment_state == 'blocked' for move in self):
            raise UserError(_(
                "No es posible registrar el pago porque tiene facturas seleccionadas "
                "que se encuentran bloqueadas para pago."
            ))
        return super().action_force_register_payment()

    def action_open_multi_payment_wizard(self):
        """Abrir el wizard de pagos múltiples con las facturas seleccionadas"""
        if not self:
            raise UserError(_('No hay facturas seleccionadas.'))
        
        # Validar que todas las facturas estén en la misma moneda
        currencies = self.mapped('currency_id')
        if len(currencies) > 1:
            raise UserError(_(
                'Todas las facturas seleccionadas deben estar en la misma moneda. '
                'Se encontraron las siguientes monedas: %s'
            ) % ', '.join(currencies.mapped('name')))
        companies = self.mapped('company_id')
        if len(companies) > 1:
            raise UserError(_(
                'Todas las facturas seleccionadas deben estar en la misma empresa. '
                'Se encontraron las siguientes empresas: %s'
            ) % ', '.join(companies.mapped('name')))
        
        # Validar que las facturas estén en estado apropiado para pago
        invalid_moves = self.filtered(
            lambda move: move.state != 'posted' or 
                        move.payment_state not in ('not_paid', 'partial') or
                        move.move_type not in ('in_invoice', 'out_invoice', 'out_receipt', 'in_receipt')
        )
        if invalid_moves:
            raise UserError(_(
                'Las siguientes facturas no pueden ser pagadas:\n%s\n\n'
                'Solo se pueden pagar facturas de cliente/proveedor que estén publicadas '
                'y con estado de pago "No pagado" o "Parcialmente pagado".'
            ) % '\n'.join(invalid_moves.mapped('display_name')))
        
        # Abrir el wizard con las facturas seleccionadas
        
        _new_context = dict(self.env.context)
        _new_context.update({
            'active_ids': self.ids,
            'active_model': 'account.move',
            'default_invoice_currency_id': currencies[0].id if currencies else False,
            'default_invoice_ids': [(6, 0, self.ids)],
            'default_move_type': self[0].move_type,
            'default_company_id': companies[0].id
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pagos Múltiples de Facturas'),
            'res_model': 'multi.invoice.payment.wizard',
            'view_mode': 'form',
            'target': 'current',
            'context': _new_context
        }
