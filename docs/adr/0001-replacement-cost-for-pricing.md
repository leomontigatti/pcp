# Price Lists compute from replacement cost

With Argentine inflation, a cost averaged over older stock trails what restocking costs, so prices computed from it
would trail the market. The **Cost** that both **Price Lists** compute from is therefore the replacement cost: the last
supplier price, after that supplier's own discounts (the purchase line's discount), plus a flat freight of 5% on every
**Product**, before IVA, updated when a purchase is received and never averaged with older stock. Pricing uses this
Cost whatever costing method stock valuation uses; how the two coexist in Odoo is left to the implementation (#20).

## Considered Options

- **AVCO or FIFO** (Odoo's native costing): they lag behind inflation.
- **Standard cost**: some 14,000 costs kept by hand.
- **Freight as landed costs** from the real freight invoices: rejected for simplicity. The old system used a flat
  per-product percentage (`COSTOFPOR`, 2–5%); a single 5% on every Product keeps that idea with one number.

Decided with the maintainer on 2026-10-22.
