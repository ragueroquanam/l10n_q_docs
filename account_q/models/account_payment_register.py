# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    vat_refund_applicable = fields.Boolean(
        string="Aplica devolución de impuestos",
        compute='_compute_vat_refund_applicable',
        readonly=True
    )

    def _get_invoice_vat_refund_flags(self):
        """
        Retorna una tupla: (invoices, doc_types_configured, applies_set)
        - invoices: recordset de account.move
        - doc_types_configured: lista de ids de l10n_latam.document.type
        - applies_set: set con valores booleanos {True, False} indicando si aplica devolución por cada factura
        """
        active_ids = self.env.context.get('active_ids', [])

        if self._context.get('active_model') == 'account.move':
            invoices = self.env['account.move'].browse(active_ids)
        elif self._context.get('active_model') == 'account.move.line':
            move_lines = self.env['account.move.line'].browse(active_ids)
            invoices = move_lines.mapped('move_id')
        else:
            invoices = self.env['account.move']

        # Buscar todos los document_type_id configurados en tax.refund.legislation.config
        # Buscar todos los document_type_id y sus tax_id configurados en tax.refund.legislation.config
        config_records = self.env['tax.refund.legislation.config'].search([
            ('document_type_id', '!=', False),
            ('tax_ids', '!=', False)
        ])
        # Construir un set de tuplas (document_type_id, tax_id) válidas
        doc_type_tax_pairs = set()
        for rec in config_records:
            for tax in rec.tax_ids:
                doc_type_tax_pairs.add((rec.document_type_id.id, tax.id))

        doc_types_configured = list({rec.document_type_id.id for rec in config_records})

        # Para cada factura, verificar si existe al menos una línea con un tax_id tal que
        # (document_type_id, tax_id) esté en la configuración
        applies_set = set(
            any(
                (inv.l10n_latam_document_type_id.id, tax_id) in doc_type_tax_pairs
                for line in inv.invoice_line_ids
                for tax_id in line.tax_ids.ids
            )
            for inv in invoices
        )
        return invoices, doc_types_configured, applies_set

    @api.depends('payment_method_line_id')
    def _compute_vat_refund_applicable(self):
        for rec in self:
            applicable = False
            method_line = rec.payment_method_line_id
            if method_line and method_line.apply_vat_refund:
                invoices, doc_types_configured, applies = rec._get_invoice_vat_refund_flags()
                if applies == {True}:
                    applicable = True
            rec.vat_refund_applicable = applicable

    def action_create_payments(self):
        if not self.env.context.get('force_skip_vat_refund_check'):
            invoices, doc_types_configured, applies = self._get_invoice_vat_refund_flags()
            if applies == {True, False}:
                return {
                    'name': 'Advertencia de devolución de IVA',
                    'type': 'ir.actions.act_window',
                    'res_model': 'vat.refund.confirmation.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': dict(self.env.context),
                }

        return super().action_create_payments()
