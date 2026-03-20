# -*- coding: utf-8 -*-

from lxml import etree
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    session_id = fields.Many2one(
        'cash.management.session',
        string="Sesión de caja",
        ondelete='set null'
    )
    user_collector_id = fields.Many2one('res.users', string="Agente de cobranza", default=lambda self: self.env.user)
    check_type = fields.Selection([
        ('delivered', 'Entregado'),
        ('received', 'Recibido'),
    ], string="Tipo de cheque")

    card_name = fields.Char(string="Nombre de la tarjeta")
    in_cashbox = fields.Boolean(string="En caja", default=False)
    check_session_id = fields.Many2one(
        'cash.management.session',
        string="Sesión de caja check",
        ondelete='set null'
    )

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        # Solo aplicamos lógica en la vista lista
        if view_type == 'list' and options['action_id']:
            doc = etree.XML(res['arch'])
            # Quitar el campo in_cashbox de la lista
            for node in doc.xpath("//field[@name='in_cashbox']"):
                node.getparent().remove(node)
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if options and options.get('toolbar') and options['action_id']:
            for view_type in res.get('views', {}):
                toolbar = res['views'][view_type].get('toolbar')
                if not toolbar:
                    continue
                # Limpiar acciones de servidor del menú acción
                if 'action' in toolbar:
                    toolbar['action'] = [
                        act for act in toolbar['action']
                        if act.get('name') not in ['➕ Sumar en caja', '➖ Quitar de caja']
                    ]
        return res

    def unlink(self):
        sessions = self.mapped('session_id')
        res = super().unlink()
        return res

    def action_refund_payment(self):
        is_cash = self.journal_id.type == 'cash'
        insufficient_balance = (self.session_id and self.session_id.balance_end < self.amount)
        is_common_bank = (self.journal_id.type == 'bank' and self.payment_method_line_id.type == 'common')

        # Evitar la cancelación de pagos si el método de pago es POS.
        if self.session_id and self.payment_method_line_id.payment_method_id.code in ('pos', 'pos_manual'):
            raise UserError(
                _("No es posible cancelar un pago realizado con el método POS desde la grilla de documentos cobrados. Para hacerlo, diríjase a la pestaña Cobros con Tarjeta."))

        if insufficient_balance and (is_cash or is_common_bank):
            raise ValidationError(_('No existe saldo en la caja para devolver este pago.'))
        if self.session_id and self.session_id.state != 'opened':
            raise ValidationError(_('No se puede cancelar un pago en una sesión de caja cerrada.'))
        if self.session_id and self.state != 'draft':
            self.action_draft()
        self.action_cancel()

    def action_cancel(self):
        context = dict(self.env.context)
        context['force_delete'] = True
        res = super(AccountPayment, self.with_context(context)).action_cancel()
        for payment in self:
            session_id = payment.session_id
            if session_id:
                if payment.session_id.state == 'opened':
                    payment.session_id = False
                    mens = "Se canceló un pago(%s) asociado a la sesión." % (payment.name or '')
                    session_id.message_post(body=_(mens))
                    if len(self) == 1:
                        return self._return_cash_session_form_action(session_id)
                else:
                    raise ValidationError(_('No se puede cancelar un pago en una sesión de caja cerrada.'))
        return res

    def action_view_details(self):
        self.ensure_one()
        context = {**self.env.context}
        context['source_session_id'] = self.session_id.id if self.session_id else False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'display_name': self._description,
            'name': self._description,
            'target': 'current',
            'view_mode': 'form',
            'res_id': self.id,
            'context': context
        }

    def _set_cash_session_from_context(self):
        context = self.env.context
        source_session_id = context.get('source_session_id')
        # self.filtered(lambda x: not x.session_id).write({'session_id': source_session_id})

        if not source_session_id:
            return

        CashManagementSession = self.env['cash.management.session']
        session = CashManagementSession.browse(source_session_id)

        if not session or session.state != 'opened':
            raise UserError(_('La sesión de caja especificada no está abierta.'))

        for rec in self.filtered(lambda x: not x.session_id):
            # Si la moneda coincide, se asigna directamente
            if rec.currency_id == session.currency_id:
                rec.session_id = session.id
            else:
                # Si no coincide, buscar una sesión abierta en la moneda del registro
                domain = [
                    ('company_id', '=', session.company_id.id),
                    ('state', '=', 'opened'),
                    '|',
                    ('config_id', 'child_of', session.config_id.id),
                    ('config_id', 'parent_of', session.config_id.id)
                ]
                if rec.currency_id.name == 'UYU':
                    domain.append(('currency_id', 'in', [rec.currency_id.id, False]))
                else:
                    domain.append(('currency_id', '=', rec.currency_id.id))

                other_session = CashManagementSession.search(domain, limit=1)
                if not other_session:
                    raise UserError(_(
                        'No se encontró una sesión de caja abierta en la moneda "%s" para el registrar el pago %s.'
                    ) % (rec.currency_id.name, rec.display_name))

                rec.session_id = other_session.id


    def _return_cash_session_form_action(self, session_id=None):
        context = self.env.context
        source_session_id = context.get('source_session_id')

        if source_session_id or session_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sesión de Caja',
                'res_model': 'cash.management.session',
                'res_id': source_session_id or session_id.id,
                'view_mode': 'form',
                'target': 'main',
            }
        return False

    def action_post(self):
        source_session_id = self.env.context.get('source_session_id')
        for rec in self:
            if source_session_id and rec.payment_type == 'outbound':
                if rec.payment_method_line_id.is_check and (not rec.in_cashbox or not rec.check_session_id):
                    raise UserError(_("No se puede pagar un cheque que no ha sido ingresado en caja."))
        super().action_post()
        self._set_cash_session_from_context()
        if source_session_id:
            for rec in self:
                rec.move_id.session_id = source_session_id
            return self._return_cash_session_form_action()

    def action_add_to_cashbox(self):
        if any(self.filtered(lambda l: l.in_cashbox)):
            raise UserError("Existen líneas que ya fueron sumadas en la caja.")

        # Buscar sesión abierta
        context = self.env.context
        source_session_id = context.get('source_session_id')
        if not source_session_id:
            raise UserError("No se encontró sesión de caja.")
        session = self.env['cash.management.session'].browse(source_session_id)

        total = sum(self.mapped('amount'))

        session.new_doc_to_pay += total
        self.write({'in_cashbox': True, 'check_session_id': session.id})

    def action_remove_from_cashbox(self):
        if any(self.filtered(lambda l: not l.in_cashbox)):
            raise UserError("Existen líneas que no fueron sumadas en la caja.")

        context = self.env.context
        source_session_id = context.get('source_session_id')
        if not source_session_id:
            raise UserError("No se encontró sesión de caja.")
        session = self.env['cash.management.session'].browse(source_session_id)

        if any(self.filtered(lambda l: not l.check_session_id != session.id)):
            raise UserError("Existen líneas que no pertenecen a la sesión actual de caja .")

        session.new_doc_to_pay -= sum(self.mapped('amount'))
        self.write({'in_cashbox': False, 'check_session_id': False})


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    session_id = fields.Many2one('cash.management.session', string="Sesión de caja", ondelete='set null')
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Producto',
        ondelete='restrict',
        check_company=True,
    )
    product_category_id = fields.Many2one(
        comodel_name='product.category',
        related='product_id.categ_id',
        store=True
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta contable',
        auto_join=True,
        ondelete="cascade",
        domain="[('deprecated', '=', False), ('account_type', '!=', 'off_balance')]",
        check_company=True,
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            if self.product_id.property_account_expense_id:
                self.account_id = self.product_id.property_account_expense_id.id
            else:
                self.account_id = self.product_category_id.property_account_expense_categ_id

    def write(self, vals):
        for record in self:
            if record.session_id and ('amount' in vals or 'account_id' in vals):
                raise UserError(
                    "No se puede modificar una transacción una vez creada. Por favor, elimínela y vuelva a crearla.")
        return super(AccountBankStatementLine, self).write(vals)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        session_id = self.env.context.get("default_session_id")
        if session_id and "journal_id" in fields_list:
            session = self.env["cash.management.session"].browse(session_id)
            if session and session.config_id.journal_id:
                res["journal_id"] = session.config_id.journal_id.id

        return res

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        vals = super()._prepare_move_line_default_vals(counterpart_account_id)
        # Modifica el account_id de la línea de contrapartida
        if len(vals) > 1 and self.account_id and self.session_id:
            vals[1]['account_id'] = self.account_id.id
        return vals

    def action_open_move(self):
        """Abrir el asiento contable relacionado"""
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asiento contable',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'target': 'current',
        }
