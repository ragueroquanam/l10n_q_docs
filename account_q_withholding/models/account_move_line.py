from odoo import fields, models, _, api, Command
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if self._context.get('is_line_withholding') and options and options.get('toolbar'):
            for view_type in res['views']:
                res['views'][view_type]['toolbar'] = {}
        return res

    resguardo_line_id = fields.Many2one(
        'account.resguardo.line',
        string='Línea de Resguardo'
    )
    resguardo_id = fields.Many2one(
        'account.resguardo',
        related='resguardo_line_id.resguardo_id',
        string='Resguardo', store=True
    )

    # MANAGEMENT OF ACCUMULATED WITHHOLDINGS
    invoice_accumulated_ids = fields.Many2many(
        'account.move',
        string='Facturas acumuladas en este impuesto'
    )

    def action_create_resguardo(self):
        AccountResguardoLine = self.env['account.resguardo.line']
        if not self:
            raise UserError(_("Debe seleccionar al menos una línea."))

        # Validaciones: mismo proveedor, misma moneda y sin resguardo
        partners = self.mapped('partner_id')
        currencys = self.mapped('currency_id')
        companies = self.mapped('company_id')
        lines_with_resguardo_qty = self.env['account.move.line'].search_count([
            ('id', 'in', self.ids),
            ('resguardo_line_id', '!=', False),
        ])

        if len(partners) > 1 or len(currencys) > 1:
            raise UserError(_("Solo puede crear un resguardo con líneas del mismo proveedor y la misma moneda."))

        if lines_with_resguardo_qty:
            raise UserError(_("Algunas líneas ya están asignadas a un resguardo."))

        if len(companies) > 1:
            raise UserError(_("Solo puede crear un resguardo con líneas de la misma compañía."))

        partner = partners[0]
        currency = currencys[0]
        company = companies and companies[0] or self.env.company

        # Crear resguardo y sus líneas
        resguardo = self.env['account.resguardo'].create({
            'name': self.env['ir.sequence'].next_by_code('account.resguardo') or '/',
            'date': fields.Date.today(),
            'partner_id': partner.id,
            'rut': partner.vat,
            'currency_id': currency.id,
            'company_id': company.id,
            'state': 'draft',
        })

        # Crear líneas del resguardo
        for line in self:
            AccountResguardoLine.create({
                'resguardo_id': resguardo.id,
                'move_line_id': line.id,
                'tax_name': line.tax_line_id.name,
                'tax_percent': line.tax_line_id.amount,
                'currency_id': line.currency_id.id,
                'base_amount': line.tax_base_amount,
                'tax_amount': line.balance,
                'total': line.tax_base_amount + line.balance,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': f'Resguardo generado correctamente: {resguardo.name}',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def button_open_resguardo(self):
        self.ensure_one()
        view_id = self.env.ref('account_q_withholding.view_account_resguardo_form').id
        context = {**self.env.context}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Resguardo'),
            'res_model': 'account.resguardo',
            'target': 'current',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'context': context,
            'res_id': self.resguardo_id.id,
        }

    def button_open_move(self):
        self.ensure_one()
        view_id = self.env.ref('account.view_move_form').id
        context = {'search_default_in_invoice': 1, 'default_move_type': 'in_invoice', 'display_account_trust': True,
                   **self.env.context}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de proveedor'),
            'res_model': 'account.move',
            'target': 'current',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'context': context,
            'res_id': self.move_id.id,
        }

    @api.onchange('product_id')
    def _onchange_product_id_set_fiscal_position_tax(self):
        if not self.product_id or not self.move_id or self.move_id.move_type != 'in_invoice':
            return

        fiscal_position = self.move_id.fiscal_position_id
        if not fiscal_position:
            return

        fiscal_position_tax = self.env['account.fiscal.position.product'].sudo().search([
            ('fiscal_position_id', '=', fiscal_position.id),
            ('product_id', '=', self.product_id.id),
        ])

        if not fiscal_position_tax:
            return

        new_tax_ids = fiscal_position_tax.tax_id.ids

        existing_tax_ids = self.tax_ids.ids
        combined_tax_ids = list(set(existing_tax_ids + new_tax_ids))

        self.tax_ids = [(6, 0, combined_tax_ids)]

        if not self.tax_ids:
            return

    # MANAGEMENT OF ACCUMULATED WITHHOLDINGS
    @api.model_create_multi
    def create(self, vals_list):
        new_lines = super().create(vals_list)
        new_lines.with_context(skip_invoice_accumulation=True)._set_invoice_to_accumulate_reference()
        return new_lines

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get('skip_invoice_accumulation'):
            self.with_context(skip_invoice_accumulation=True)._set_invoice_to_accumulate_reference()
        return result

    def _set_invoice_to_accumulate_reference(self):
        for line in self:
            if line.move_id.move_type == 'in_invoice' and line.display_type == 'tax' and line.tax_line_id.applies_to == 'monthly':
                _invoices_accumulated = line.tax_line_id._get_in_invoice_to_accumulate(line.move_id).get(
                    'invoices_out_system')
                line.invoice_accumulated_ids = [Command.set(_invoices_accumulated.ids)]
