from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cost_freight = fields.Float(related="company_id.cost_freight", readonly=False)
    pack_discount = fields.Float(related="company_id.pack_discount", readonly=False)
