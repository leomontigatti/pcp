from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        # A free line (a bonificación at price 0 or 100% off) or a credit (below 0) is not a supplier price.
        received = moves.filtered(
            lambda m: (
                m.state == "done" and m.purchase_line_id.price_unit_discounted > 0 and m.location_id.usage == "supplier"
            )
        )
        # A warehouse user may validate a receipt without the right to edit products; the Cost is
        # derived from the receipt itself, so it is written as superuser.
        for move in received.sorted(lambda m: (m.date, m.id)):
            move.product_id.sudo().replacement_cost = move.purchase_line_id._replacement_cost()
        return moves
