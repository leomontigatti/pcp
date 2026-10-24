# Odoo 19 Community with ADHOC's Argentine localization

PCP needs a self-hosted Odoo 19 on Coolify that issues comprobantes with a CAE from ARCA (Factura A and B, credit
notes, the point of sale), applies IIBB Córdoba Perceptions on supplier bills, handles Withholdings and produces the
libro IVA, on a small business's budget. Odoo Community's own `l10n_ar` gives the chart of accounts, taxes and
document types but no ARCA web service, so PCP runs Community with ADHOC's AGPL-3 modules (ingadhoc):
`l10n_ar_fiscal_ws` for WSFE, the CAE and the QR, and `l10n_ar_tax` for Perceptions and Withholdings. The pinned
repos are in `prototype/repos.txt`. The deployed prototype got real CAEs on 2026-10-01 for FA-A 00001-00000001 and
00001-00000002, FA-B 00002-00000001 and NC-A 00001-00000001.

The choice came with the scaffold (a0916c9, 2026-09-25) and nobody wrote down why at the time. This ADR
reconstructs the reasons from research done on 2026-10-23.

## Considered Options

- **Odoo Enterprise**: ARCA invoicing is `l10n_ar_edi`, which Odoo documents but does not ship in its public
  source. It is billed per user per month plus IVA, and only the dearer Custom plan allows self-hosting; Standard
  is Odoo Online only. The figures on the pricing page differed between the 2026-10-23 research and a reading on
  2026-10-24, so none is recorded here. Its docs did not confirm a CAE from the point of sale or Córdoba
  Perceptions.
- **OCA `l10n-argentina`**: its 19.0 branch has no addons yet; the migration issue (OCA/l10n-argentina#89) is still
  open.
- **Community core alone**: no CAE, so it cannot invoice.

## Consequences

- PCP moves at ADHOC's release pace, so the addons are pinned to exact commits and move only through
  `uv run just bump-addons`.
- The localization is several repos (odoo-argentina, odoo-argentina-ce, account-payment, account-financial-tools,
  account-invoicing) whose dependencies move together.
- There is no support contract by default. ADHOC sells support separately; its terms were not checked.
- Leaving costs a data migration, not licences.
- Known gap: a WSFE journal cannot post without an ARCA certificate (`prototype/README.md`).
- Still open: a CAE from a point-of-sale sale, and IIBB Córdoba Perceptions on a real supplier bill.

Sources, checked 2026-10-24: Odoo's
[Argentina localization docs](https://www.odoo.com/documentation/19.0/es_419/applications/finance/fiscal_localizations/argentina.html),
[`addons/l10n_ar` on 19.0](https://github.com/odoo/odoo/tree/19.0/addons/l10n_ar),
[pricing](https://www.odoo.com/es/pricing) (a live page, subject to change),
[OCA l10n-argentina 19.0](https://github.com/OCA/l10n-argentina/tree/19.0) and
[its issue #89](https://github.com/OCA/l10n-argentina/issues/89).
