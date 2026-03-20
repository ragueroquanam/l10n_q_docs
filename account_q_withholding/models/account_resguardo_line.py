from odoo import models, fields, api


class AccountResguardoLine(models.Model):
    _name = 'account.resguardo.line'
    _description = 'Detalle de Resguardo'

    resguardo_id = fields.Many2one(
        'account.resguardo',
        string='Resguardo',
        required=True, ondelete='cascade'
    )
    move_line_id = fields.Many2one(
        'account.move.line',
        string='Línea Contable',
        required=True,
        readonly=True
    )
    tax_name = fields.Char(string='Impuesto')
    tax_percent = fields.Float(string='Porcentaje (%)')
    currency_id = fields.Many2one(
        related='resguardo_id.currency_id',
        store=True,
        readonly=True
    )
    base_amount = fields.Monetary(string='Base de Cálculo')
    tax_amount = fields.Monetary(string='Importe Retención')
    total = fields.Monetary(string='Total')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for res in records:
            if res.resguardo_id.state == 'done' and res.move_line_id:
                res.move_line_id.resguardo_line_id = res
        return records

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            if line.resguardo_id.state == 'done' and line.move_line_id:
                line.move_line_id.resguardo_line_id = line
        return res
