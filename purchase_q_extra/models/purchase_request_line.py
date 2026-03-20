from odoo import models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def _prepare_purchase_order_line(self, order, item):
        res = super()._prepare_purchase_order_line(order, item)
        if item.line_id.specifications:
            res['specifications'] = item.line_id.specifications
        return res
