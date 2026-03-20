from odoo.tests.common import tagged
from odoo.addons.purchase.tests.test_access_rights import TestPurchaseInvoice


@tagged('post_install', '-at_install')
class TestPurchaseInvoiceExtended(TestPurchaseInvoice):

    def test_double_validation(self):
        """Only purchase managers can approve a purchase order when double
        validation is enabled"""
        group_purchase_manager = self.env.ref('purchase.group_purchase_manager')
        order = self.env['purchase.order'].create({
            "partner_id": self.vendor.id,
            "order_line": [
                (0, 0, {
                    'product_id': self.product.id,
                    'name': f'{self.product.name} {1:05}',
                    'price_unit': 79.80,
                    'product_qty': 15.0,
                }),
            ]})
        company = order.sudo().company_id
        company.po_double_validation = 'two_step'
        company.po_double_validation_amount = 0
        self.purchase_user.write({
            'company_ids': [(4, company.id)],
            'company_id': company.id,
            'groups_id': [(3, group_purchase_manager.id)],
        })
        order.with_user(self.purchase_user).button_confirm()
        self.assertEqual(order.state, 'to approve')
        order.with_user(self.purchase_user).button_approve()
        self.assertEqual(order.state, 'to approve')
        self.purchase_user.groups_id += group_purchase_manager
        order.with_user(self.purchase_user).button_approve()
        self.assertEqual(order.state, 'purchase')
