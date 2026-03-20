from odoo import models, fields


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    product_map_ids = fields.One2many(
        'account.fiscal.position.product',
        'fiscal_position_id',
        string='Mapeo de Producto')


class AccountFiscalPositionProduct(models.Model):
    _name = 'account.fiscal.position.product'
    _description = 'Mapeo de Producto para Posición Fiscal'

    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        ondelete='cascade')
    product_id = fields.Many2one(
        'product.product',
        string='Producto')
    tax_id = fields.Many2one(
        'account.tax',
        string='Impuesto/Retención',
        required=True)

    _sql_constraints = [
        ('product_tax_uniq',
         'unique (product_id,tax_id)',
         'Solo se puede definir una vez el mismo impuesto por producto.')
    ]
