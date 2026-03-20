from odoo import fields, models, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    tax_withholding = fields.Boolean(string='Retención')
    tax_withholding_applies_to = fields.Selection(
        [('base', 'Base'), ('tax', 'Impuesto')],
        string='Retención aplica sobre'
    )
    account_tax_id = fields.Many2one(
        'account.tax',
        string='Impuesto',
        domain="[('tax_withholding', '=', False), ('type_tax_use', '=', type_tax_use)]"
    )
    account_tax_ids = fields.Many2many(
        'account.tax',
        'withholding_account_tax_account_tax_id_rel',
        'withholding_account_tax_id',
        'account_tax_id',
        string='Impuestos',
        domain="[('tax_withholding', '=', False), ('type_tax_use', '=', type_tax_use)]"
    )
    applies_to = fields.Selection(
        [('monthly', 'Mensual acumulado')],
        string='Aplica para', required=False)
    imponible_condition = fields.Selection(
        [('greater_than', 'Mayor que')],
        string='Monto imponible')
    imponible_amount = fields.Float()
    imponible_currency_id = fields.Many2one('res.currency')

    @api.onchange('tax_withholding_applies_to')
    def _onchange_tax_withholding_applies_to(self):
        if self.tax_withholding_applies_to != 'tax':
            self.account_tax_id = False
            self.account_tax_ids = False

    @api.onchange('tax_withholding')
    def _onchange_tax_withholding(self):
        if not self.tax_withholding:
            self.tax_withholding_applies_to = False
            self.account_tax_id = False
            self.account_tax_ids = False

    @api.onchange('applies_to')
    def _onchange_applies_to(self):
        if not self.applies_to:
            self.imponible_condition = False
            self.imponible_amount = float(0)
            self.imponible_currency_id = False

    def _get_tax_details(  # flake8: noqa: C901
            self,
            price_unit,
            quantity,
            precision_rounding=0.01,
            rounding_method='round_per_line',
            product=None,
            product_uom=None,
            special_mode=False,
            manual_tax_amounts=None,
            filter_tax_function=None,
    ):

        tax_result = super()._get_tax_details(
            price_unit=price_unit,
            quantity=quantity,
            precision_rounding=precision_rounding,
            rounding_method=rounding_method,
            product=product,
            product_uom=product_uom,
            special_mode=special_mode,
            manual_tax_amounts=manual_tax_amounts,
            filter_tax_function=filter_tax_function
        )

        move_id = self.env.context.get('move')
        if self.env.context.get('ignore_account_q_withholding') or (move_id and move_id.move_type not in ('in_invoice', 'in_refund')):
            return tax_result

        move_current_tax_base_map = {}

        if move_id:
            base_lines, _tax_lines = move_id.with_context(
                ignore_account_q_withholding=True
            )._get_rounded_base_and_tax_lines()

            for base_line in base_lines:
                tax_details = base_line.get('tax_details', {})
                for td in tax_details.get('taxes_data', []):
                    tax = td.get('tax')
                    if not tax or not tax.tax_withholding:
                        continue

                    move_current_tax_base_map.setdefault(tax.id, 0.0)
                    move_current_tax_base_map[tax.id] += td.get('base_amount', 0.0)

        for tax_data in tax_result['taxes_data']:
            tax = tax_data['tax']
            if tax.tax_withholding and tax.tax_withholding_applies_to == 'tax' and not tax.applies_to == 'monthly':
                if tax.account_tax_ids:
                    related_tax_amount = next(
                        (td['tax_amount'] for td in tax_result['taxes_data'] if td['tax'].id in tax.account_tax_ids.ids),
                        0.0)
                else:
                    related_tax_amount = sum(
                        td['tax_amount'] for td in tax_result['taxes_data'] if not td['tax'].tax_withholding)

                if related_tax_amount and tax.amount_type == 'percent':
                    tax_data['tax_amount'] = related_tax_amount * tax.amount / 100.0
                    tax_data['base_amount'] = related_tax_amount

            elif tax.tax_withholding and tax.applies_to == 'monthly' and move_id:
                if tax.imponible_condition == 'greater_than' and tax.imponible_amount > 0:
                    if tax.imponible_currency_id:
                        imponible_amount = tax.imponible_currency_id._convert(
                            tax.imponible_amount,
                            self.env.company.currency_id,
                            self.env.company,
                            self.env.context.get('date', fields.Date.today())
                        )
                    else:
                        imponible_amount = tax.imponible_amount

                    old_moves_dict = tax._get_in_invoice_to_accumulate(move_id)
                    old_monthly_move_with_this_tax = self.env['account.move']
                    _tax_amount = float(0)
                    _base_amount = float(0)
                    total_accumulated_tax_amount = float(0)
                    total_accumulated_base_amount = float(0)
                    for old_monthly_move in old_moves_dict.get('invoices_in_system'):
                        x = old_monthly_move.with_context(
                            ignore_account_q_withholding=True)._get_rounded_base_and_tax_lines()
                        for base_line in x[0]:  # x[0] es la lista de líneas base
                            tax_details = base_line.get('tax_details', {})
                            old_taxes_data = tax_details.get('taxes_data', [])

                            for old_tax_data in old_taxes_data:
                                if old_tax_data.get('tax') == tax:
                                    total_accumulated_tax_amount += old_tax_data.get('tax_amount', 0.0)
                                    total_accumulated_base_amount += old_tax_data.get('base_amount', 0.0)
                                    break

                    for old_monthly_move in old_moves_dict.get('invoices_out_system'):
                        is_my_reversed_move = move_id.move_type == 'in_refund' and move_id.reversed_entry_id == old_monthly_move
                        if not is_my_reversed_move:
                            # Este bloque se ejecuta cuando se están procesando facturas de tipo "in_refund" (notas de crédito de proveedor)
                            # y se verifica si el movimiento actual es una reversión directa del movimiento anterior.
                            # Si no es una reversión, se aplica el contexto para ignorar la retención de impuestos al obtener las líneas base y de impuestos.
                            # Esto es relevante para evitar duplicar o considerar indebidamente retenciones en movimientos que ya han sido revertidos.
                            old_monthly_move = old_monthly_move.with_context(
                                ignore_account_q_withholding=True)
                        x = old_monthly_move._get_rounded_base_and_tax_lines()

                        for base_line in x[0]:  # x[0] es la lista de líneas base
                            tax_details = base_line.get('tax_details', {})
                            old_taxes_data = tax_details.get('taxes_data', [])

                            for old_tax_data in old_taxes_data:
                                if old_tax_data.get('tax') == tax:
                                    old_monthly_move_with_this_tax |= old_monthly_move
                                    _tax_amount += old_tax_data.get('tax_amount', 0.0)
                                    _base_amount += old_tax_data.get('base_amount', 0.0)
                                    total_accumulated_tax_amount += old_tax_data.get('tax_amount', 0.0)
                                    total_accumulated_base_amount += old_tax_data.get('base_amount', 0.0)
                                    break

                    # REFUNDS: SE ESTA EVALUANDO
                    for old_monthly_move in old_moves_dict.get('refunds_in_system'):
                        x = old_monthly_move.with_context(
                            ignore_account_q_withholding=True)._get_rounded_base_and_tax_lines()

                        for base_line in x[0]:  # x[0] es la lista de líneas base
                            tax_details = base_line.get('tax_details', {})
                            old_taxes_data = tax_details.get('taxes_data', [])

                            for old_tax_data in old_taxes_data:
                                if old_tax_data.get('tax') == tax:
                                    old_monthly_move_with_this_tax |= old_monthly_move
                                    _tax_amount -= old_tax_data.get('tax_amount', 0.0)
                                    _base_amount -= old_tax_data.get('base_amount', 0.0)
                                    total_accumulated_tax_amount -= old_tax_data.get('tax_amount', 0.0)
                                    total_accumulated_base_amount -= old_tax_data.get('base_amount', 0.0)
                                    break

                    if move_id.move_type != 'in_refund':
                        # Este bloque se ejecuta cuando el movimiento actual NO es una nota de crédito de proveedor ("in_refund").
                        # Aquí se acumula el monto base de la retención correspondiente a la factura o documento actual.
                        # total_accumulated_base_amount += tax_data['base_amount']
                        # _base_amount = _base_amount + tax_data['base_amount']
                        current_move_base = move_current_tax_base_map.get(tax.id, 0.0)
                        total_accumulated_base_amount += current_move_base
                        _base_amount += current_move_base

                    if total_accumulated_base_amount > imponible_amount:
                        if tax.tax_withholding and tax.tax_withholding_applies_to == 'tax':
                            if tax.account_tax_ids:
                                related_tax_amount = next(
                                    (td['tax_amount'] for td in tax_result['taxes_data'] if
                                     td['tax'].id in tax.account_tax_ids.ids),
                                    0.0)
                            else:
                                related_tax_amount = sum(
                                    td['tax_amount'] for td in tax_result['taxes_data'] if
                                    not td['tax'].tax_withholding)

                            if related_tax_amount and tax.amount_type == 'percent':
                                tax_data['tax_amount'] = related_tax_amount * tax.amount / 100.0
                                tax_data['base_amount'] = related_tax_amount
                        else:
                            tax_data['tax_amount'] = _tax_amount + tax_data['tax_amount']
                            tax_data['base_amount'] = _base_amount
                    else:
                        tax_data['tax_amount'] = 0.0
        return tax_result

    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        super()._add_tax_details_in_base_line(
            base_line, company, rounding_method=None)

        price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        taxes_computation = base_line['tax_ids']._get_tax_details(
            price_unit=price_unit_after_discount,
            quantity=base_line['quantity'],
            precision_rounding=base_line['currency_id'].rounding,
            rounding_method=rounding_method or company.tax_calculation_rounding_method,
            product=base_line['product_id'],
            product_uom=base_line['product_uom_id'],
            special_mode=base_line['special_mode'],
            manual_tax_amounts=base_line['manual_tax_amounts'],
            filter_tax_function=base_line['filter_tax_function'],
        )
        tax_details = base_line['tax_details']

        for tax_data in taxes_computation['taxes_data']:
            if 'move_ids' in tax_data:
                tax_details['move_ids'] = tax_data.get('move_ids', ())

    def _get_in_invoice_to_accumulate(self, invoice):
        date_start = fields.Date.from_string(invoice.date).replace(day=1)
        invoices_in_system = self.env['account.move.line'].search([
            ('move_id.partner_id', '=', invoice.partner_id.id),
            ('move_id.date', '>=', date_start),
            ('move_id.date', '<=', invoice.date),
            ('move_id.state', 'not in', ('cancel', 'draft')),
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.id', '!=', invoice.id),
            ('tax_line_id', '=', self.id),
        ]).mapped('invoice_accumulated_ids')
        invoices_in_system |= self.env['account.move.line'].search([
            ('move_id.partner_id', '=', invoice.partner_id.id),
            ('move_id.date', '>=', date_start),
            ('move_id.date', '<=', invoice.date),
            ('move_id.state', 'not in', ('cancel', 'draft')),
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.id', '!=', invoice.id),
            ('tax_line_id', '=', self.id),
        ]).mapped('move_id')
        invoices_out_system = self.env['account.move'].search([
            ('partner_id', '=', invoice.partner_id.id),
            ('date', '>=', date_start),
            ('date', '<=', invoice.date),
            ('state', 'not in', ('cancel', 'draft')),
            ('move_type', '=', 'in_invoice'),
            ('id', '!=', invoice.id),
            ('id', 'not in', invoices_in_system.ids),
        ])
        refunds_in_system = self.env['account.move.line'].search([
            ('move_id.partner_id', '=', invoice.partner_id.id),
            ('move_id.date', '>=', date_start),
            ('move_id.date', '<=', invoice.date),
            ('move_id.state', 'not in', ('cancel', 'draft')),
            ('move_id.move_type', '=', 'in_refund'),
            ('move_id.id', '!=', invoice.id),
            ('tax_line_id', '=', self.id),
        ]).mapped('move_id')
        refunds_in_system |= self.env['account.move'].search([
            ('partner_id', '=', invoice.partner_id.id),
            ('date', '>=', date_start),
            ('date', '<=', invoice.date),
            ('state', 'not in', ('cancel', 'draft')),
            ('move_type', '=', 'in_refund'),
            ('id', '!=', invoice.id),
        ])
        return {
            'invoices_in_system': invoices_in_system,
            'invoices_out_system': invoices_out_system,
            'refunds_in_system': refunds_in_system,
        }
