# Price Lists compute from replacement cost

The **Cost** that both **Price Lists** compute from is the replacement cost: the last supplier price, after that
supplier's own discounts (the purchase line's discount), plus a flat freight of 5% on every **Product**, before IVA.
It is updated when a purchase is received and is never averaged with older stock. With Argentine inflation, Odoo's
native AVCO and FIFO lag behind what restocking costs, so prices computed from them would trail the market; a
Standard cost would mean keeping some 14,000 costs by hand. Pricing uses this Cost whatever costing method stock
valuation uses; how the two coexist in Odoo is left to the implementation (#20). Decided with the maintainer on
2026-10-22.

## Considered Options

- **AVCO or FIFO** (Odoo's native costing): rejected, they lag behind inflation.
- **Standard cost**: rejected, ~14,000 costs kept by hand.
- **Freight as landed costs** from the real freight invoices: rejected for simplicity. The old system used a flat
  per-product percentage (`COSTOFPOR`, 2–5%); a single 5% on every Product keeps that idea with one number.
