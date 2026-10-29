from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends("order_id.partner_id", "order_id.pricelist_id")
    def _compute_discount(self):
        res = super()._compute_discount()
        for line in self.filtered(lambda ln: ln.product_id and not ln.display_type and not ln.combo_item_id):
            pricelist = line.order_id.pricelist_id
            if pricelist.list_kind:
                line.discount = pricelist.line_discount(
                    line.order_id.partner_id, line.product_id, line.product_uom_qty, line.product_uom_id
                )
        return res
