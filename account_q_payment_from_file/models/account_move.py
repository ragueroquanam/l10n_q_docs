from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    file_barcode = fields.Char(
        string="Código de Barras de Archivo",
        help="Código de barras usado para el procesamiento de archivos de pago (Red Pagos/Abitab/etc.)",
        copy=False,
    )

