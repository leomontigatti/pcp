from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cost_freight = fields.Float(
        string="Flete sobre el costo (%)",
        default=5.0,
        help="Lo que se suma al precio de compra, después de los descuentos del proveedor, para dar el costo.",
    )
    pack_discount = fields.Float(
        string="Descuento por bulto cerrado (%)",
        default=5.0,
        help="Lo que se suma al descuento del cliente mayorista en una línea de bultos cerrados.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["pack_discount"]
