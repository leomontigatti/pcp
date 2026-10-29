from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_discount = fields.Float(
        string="Descuento del cliente (%)",
        help="Lo que el cliente mayorista recibe de descuento en cada línea que compra en la lista mayorista.",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ["customer_discount"]

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["customer_discount"]
