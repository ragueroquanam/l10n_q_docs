from odoo import models, fields, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        self._check_post_is_valid()
        return super(AccountMove, self).action_post()

    def button_update_tax_totals(self):
        self.ensure_one()
        self._compute_tax_totals()

    def _check_post_is_valid(self):
        """
        Validates that the invoice can be posted by checking for draft invoices
        with accumulated taxes that could conflict with the current invoice.
        This method ensures that when posting an invoice with monthly accumulated
        taxes, there are no other draft invoices for the same partner in the
        same month that also have the same accumulated tax. This prevents
        conflicts in tax accumulation calculations.

        Raises:
            ValidationError: If there are draft invoices with conflicting
                           accumulated taxes for the same partner and month.

        Returns:
            None: If validation passes successfully.
        """
        if not self:
            return True
        move_lines = self.line_ids.filtered(lambda x: x.tax_line_id.applies_to == 'monthly')
        date_start = fields.Date.from_string(self.date).replace(day=1)
        for move_line in move_lines:
            if self.env['account.move.line'].search_count([
                ('move_id.partner_id', '=', self.partner_id.id),
                ('move_id.date', '>=', date_start),
                ('move_id.date', '<=', self.date),
                ('move_id.state', '=', 'draft'),
                ('move_id.move_type', '=', 'in_invoice'),
                ('move_id.id', '!=', self.id),
                ('tax_line_id', '=', move_line.tax_line_id.id),
            ]):
                raise ValidationError(_("No se puede Confirmar la factura porque hay facturas en estado borrador que tienen el impuesto acumulado %s." % move_line.tax_line_id.display_name))

    def _get_rounded_base_and_tax_lines(self, round_from_tax_lines=True):
        self.ensure_one()
        result = super(AccountMove, self.with_context(move=self))._get_rounded_base_and_tax_lines(
            round_from_tax_lines=round_from_tax_lines)
        return result
