from odoo import api, fields, models
from odoo.tools import float_is_zero

COST_HELP = (
    "Último precio de compra, con los descuentos del proveedor y el flete, sin IVA. "
    "Las listas de precios se calculan desde este costo."
)
PACK_HELP = "Cuántas unidades de venta trae el bulto cerrado. Vacío o 0: no se vende por bulto."


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Both live on the variant, which is the Product with its own stock and supplier price; the
    # template shows them while it has a single variant, as Odoo does for the barcode.
    replacement_cost = fields.Float(
        string="Costo de reposición",
        compute="_compute_replacement_cost",
        inverse="_inverse_replacement_cost",
        help=COST_HELP,
    )
    pack_size = fields.Integer(
        string="Unidades por bulto",
        compute="_compute_pack_size",
        inverse="_inverse_pack_size",
        help=PACK_HELP,
    )

    @api.depends("product_variant_ids.replacement_cost")
    def _compute_replacement_cost(self):
        self._compute_template_field_from_variant_field("replacement_cost")

    def _inverse_replacement_cost(self):
        self._set_product_variant_field("replacement_cost")

    @api.depends("product_variant_ids.pack_size")
    def _compute_pack_size(self):
        self._compute_template_field_from_variant_field("pack_size")

    def _inverse_pack_size(self):
        self._set_product_variant_field("pack_size")

    def _get_related_fields_variant_template(self):
        return super()._get_related_fields_variant_template() + ["replacement_cost", "pack_size"]

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["replacement_cost"]


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Pricing's Cost, kept apart from standard_price so stock valuation can use any costing method
    # (docs/adr/0001-replacement-cost-for-pricing.md).
    # No digits: a Cost is never rounded, and the Price Lists compute from it.
    replacement_cost = fields.Float(string="Costo de reposición", help=COST_HELP)
    pack_size = fields.Integer(string="Unidades por bulto", help=PACK_HELP)

    def is_whole_packs(self, qty):
        """Whether `qty`, in the product's unit, is a whole, nonzero number of its Packs."""
        self.ensure_one()
        if self.pack_size <= 0 or qty <= 0:
            return False
        packs = qty / self.pack_size
        return float_is_zero(packs - round(packs), precision_digits=6)

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["replacement_cost", "pack_size"]
