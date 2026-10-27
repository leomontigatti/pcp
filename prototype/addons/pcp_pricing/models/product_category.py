from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    wholesale_margin = fields.Float(
        string="Margen mayorista (%)", help="Lo que este rubro suma al costo en la lista mayorista, antes del IVA."
    )
    retail_margin = fields.Float(
        string="Margen minorista (%)", help="Lo que este rubro suma al costo en la lista minorista, antes del IVA."
    )

    def margin_for(self, list_kind):
        self.ensure_one()
        return self.wholesale_margin if list_kind == "wholesale" else self.retail_margin

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["wholesale_margin", "retail_margin"]
