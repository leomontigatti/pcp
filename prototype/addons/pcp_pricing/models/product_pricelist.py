from odoo import api, fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    list_kind = fields.Selection(
        [("retail", "Minorista"), ("wholesale", "Mayorista")],
        string="Tipo de lista",
        help="Qué margen del rubro usa la lista, y si sus clientes reciben el descuento del cliente y por bulto.",
    )

    def line_discount(self, partner, product, qty, uom=None):
        """The Customer Discount, plus the Pack Discount on whole Packs, for a line sold on this list.

        Only the Wholesale List discounts: a Retail Customer pays the list price.
        """
        if not self or self.list_kind != "wholesale":
            return 0.0
        discount = partner.commercial_partner_id.customer_discount
        if uom and uom != product.uom_id:
            qty = uom._compute_quantity(qty, product.uom_id)
        if product.is_whole_packs(qty):
            discount += self.env.company.pack_discount
        return discount

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["list_kind"]
