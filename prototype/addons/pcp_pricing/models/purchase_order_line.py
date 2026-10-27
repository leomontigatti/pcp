from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _replacement_cost(self):
        """One product unit at this line's price after the supplier's discount, plus freight, before IVA."""
        self.ensure_one()
        taxes = self.env["account.tax"]
        base_line = taxes._prepare_base_line_for_taxes_computation(
            None,  # the line itself would add its discount a second time
            price_unit=self.price_unit_discounted,
            quantity=1,
            tax_ids=self.tax_ids,
            currency_id=self.currency_id,
            product_id=self.product_id,
            partner_id=self.partner_id,
        )
        taxes._add_tax_details_in_base_line(base_line, self.company_id)
        # The raw total: compute_all would round the Cost to cents, and a Cost is never rounded.
        price = base_line["tax_details"]["raw_total_excluded_currency"]
        price = self.product_uom_id._compute_price(price, self.product_id.uom_id)
        company = self.company_id
        today = fields.Date.context_today(self)
        price = self.currency_id._convert(price, company.currency_id, company, today, round=False)
        return price * (1 + company.cost_freight / 100)
