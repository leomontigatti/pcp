from odoo import fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    base = fields.Selection(
        selection_add=[("category_margin", "Costo + margen del rubro")],
        ondelete={"category_margin": "set default"},
    )

    def _compute_base_price(self, product, quantity, uom, date, currency, **kwargs):
        if self.base != "category_margin" or not product.categ_id:
            return super()._compute_base_price(product, quantity, uom, date, currency, **kwargs)
        margin = product.categ_id.margin_for(self.pricelist_id.list_kind)
        price = product.replacement_cost * (1 + margin / 100)
        if uom and uom != product.uom_id:
            price = product.uom_id._compute_price(price, uom)
        company = self.env.company
        return company.currency_id._convert(price, currency, company, date, round=False)
