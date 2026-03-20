from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountResguardo(models.Model):
    _name = 'account.resguardo'
    _description = 'Resguardos'
    _inherit = 'mail.thread.main.attachment'

    name = fields.Char(string='Nombre', required=True)
    date = fields.Date(string='Fecha', required=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Beneficiario',
        domain=[('supplier_rank', '>', 0)],
        required=True
    )
    rut = fields.Char(string='RUT')
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True
    )
    amount = fields.Monetary(string='Importe', compute='_compute_amount', store=True, currency_field='currency_id')
    resguardo_data = fields.Char(string='Resguardo')
    resguardo_line_ids = fields.One2many(
        'account.resguardo.line',
        'resguardo_id',
        string='Líneas de Resguardo'
    )
    state = fields.Selection(
        [('draft', 'Borrador'), ('done', 'Hecho'), ('send', 'Enviado')],
        string='Estado',
        default="draft",
        store=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        # default=lambda self: self.env.company
    )

    @api.depends('resguardo_line_ids')
    def _compute_amount(self):
        for rec in self:
            rec.amount = sum(rec.resguardo_line_ids.mapped('tax_amount'))

    def unlink(self):
        for resguardo in self:
            if resguardo.state != 'draft':
                raise UserError("Solo se puede eliminar un resguardo en estado 'Borrador'.")
        return super(AccountResguardo, self).unlink()

    def action_validate(self):
        for resguardo in self:
            if not resguardo.resguardo_line_ids:
                raise UserError(_(
                    "La validación no es posible porque no se han ingresado líneas de retención"))
            for line in resguardo.resguardo_line_ids:
                if line.move_line_id.resguardo_id and line.move_line_id.resguardo_id.state == 'done':
                    raise UserError(_(
                        "Alguna retención ya está en un resguardo validado: %s" % line.move_line_id.resguardo_id.name
                    ))
                line.move_line_id.write({'resguardo_line_id': line.id})
        self.write({'state': 'done'})

    def action_cancel(self):
        self.mapped('resguardo_line_ids.move_line_id').write({'resguardo_line_id': False})
        self.write({'state': 'draft'})

    def action_send(self):
        if self.filtered(lambda r: not r.resguardo_data):
            raise UserError(_("El campo Resguardo no puede estar vacío."))
        self.write({'state': 'send'})
