# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountBatchPaymentFileConfig(models.Model):
    _name = "account.bank.payment.file.config"
    _description = "Configuración de archivo de pago bancario"

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código", required=True)
    column_separator = fields.Char(string='Separador')
    is_recheck_file = fields.Boolean(
        string="Chequear nuevamente el archivo al Regenerar el archivo de exportación",
        default=True
    )
    header_ids = fields.One2many(
        string="Encabezados",
        comodel_name="account.bank.payment.file.config.line",
        inverse_name="config_h_id",
    )
    line_ids = fields.One2many(
        string="Líneas",
        comodel_name="account.bank.payment.file.config.line",
        inverse_name="config_id",
    )
    footer_ids = fields.One2many(
        string="Línea de cierre",
        comodel_name="account.bank.payment.file.config.line",
        inverse_name="config_f_id",
    )

    _sql_constraints = [
        ("name_uniq", "unique(name)", "El nombre de la configuración ya existe."),
        ("code_uniq", "unique(code)", "El código de la configuración ya existe."),
    ]

    def _generate_payment_file(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """
        
        return ""

    def check_payments_for_errors(self, payments):
        """ To be overridden by modules adding support for different export format. Ex: ITAU, Brou, etc.
        Params:
            payments: List of payments to process.
        """

        return []

    def _get_mapped_value(self, config_line, odoo_value, column_title, payment, result_list):
        """
        Helper to get mapped value or append error if mapping fails.
        """
        _base_title = _("%s:La configuración no pudo identificar el mapeo para el campo %s con valor %s")
        if not config_line:
            return ""
        elif config_line.type == 'mapping':
            try:
                c_map = dict(pair.split('=') for pair in config_line.value.split(','))                
            except Exception as e:
                c_map = {}
                result_list.append({
                    'title': _base_title % (self.name, column_title, odoo_value),
                    'records': payment,
                    'help_message': _("La configuración del mapeo no es adecuada. Debe ser similar a: valor_odoo1:valor_archivo1,valor_odoo2:valor_archivo2,etc.")
                })
            mapped = c_map.get(odoo_value, False)
            if not mapped:
                result_list.append({
                    'title': _base_title % (self.name,column_title, odoo_value),
                    'records': payment,
                    'help_message': _("")
                })
            return mapped or ""
        else:
            return config_line.value or ""

    def _get_card_info(self, payment):
        affiliate = self._context.get('affiliate', False)
        return payment.partner_id.with_context(affiliate=affiliate)._get_card_info()

    def _get_patner_socio(self, payment):
        return payment.partner_id.ref


class AccountBatchPaymentFileConfigLine(models.Model):
    _name = "account.bank.payment.file.config.line"
    _description = "Configuración de archivo de pago bancario - Linea"

    config_id = fields.Many2one(
        string="Configuración",
        comodel_name="account.bank.payment.file.config",
        ondelete="cascade",
    )
    config_h_id = fields.Many2one(
        string="Configuración",
        comodel_name="account.bank.payment.file.config",
        ondelete="cascade",
    )
    config_f_id = fields.Many2one(
        string="Configuración",
        comodel_name="account.bank.payment.file.config",
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Variable", required=True)
    name = fields.Char(string="Nombre", required=True)
    description = fields.Text(string="Descripción")
    type = fields.Selection(
        string="Tipo",
        selection=[
            ("fixed", "Fijo"),
            ("mapping", "Mapeo"),
        ],
        required=True,
    )
    model_id = fields.Many2one(
        string="Modelo",
        comodel_name="ir.model",
        domain="[('model', 'in', ['account.move', 'account.move.line','account.payment','res.currency', 'res.partner', 'res.partner.bank'])]",
    )
    field_id = fields.Many2one(
        string="Campo",
        comodel_name="ir.model.fields",
        domain="[('model_id', '=', model_id)]",
    )
    value = fields.Char(string="Valor", required=True)

    @api.constrains("sequence")
    def _constrains_sequence(self):
        for record in self:
            if record.sequence <= 0:
                raise ValidationError(
                    _("El valor de la Variable en las lineas debe ser mayor a 0.")
                )

    @api.onchange("type")
    def _onchange_type(self):
        if type != "mapping":
            self.model_id = False
            self.field_id = False

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.field_id = False
