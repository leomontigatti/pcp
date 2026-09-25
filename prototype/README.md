# Prototype: Odoo 19 CE + ADHOC Argentine localization on Coolify

Throwaway environment to answer one question: does Odoo 19 Community with the ADHOC
modules issue valid electronic invoices against ARCA's homologación web service, for
this company's shape (one CUIT, one Fiscal Point per Warehouse and Retail Store, POS
sales, wholesale price lists, supplier bills with IIBB perceptions)?

Nothing here is production. No customer data goes in.

## Layout

- `Dockerfile` builds `odoo:19.0` plus every addons repo listed in `repos.txt`.
- `repos.txt` pins repo, URL and branch. Change a pin, redeploy.
- `config/odoo.conf` runs Odoo threaded behind Coolify's Traefik.
- `docker-compose.yaml` is what Coolify deploys: Postgres 16 + Odoo.
- `addons/pcp/` is empty for now. Project addons go here later.

## Deploy on Coolify

1. Project: create `pcp`, environment `prototype`.
2. Resource: New → Docker Compose → Public repository `https://github.com/leomontigatti/pcp`,
   branch `main`, base directory `/prototype`, compose file `docker-compose.yaml`.
3. Environment variables: `DB_PASSWORD` and `ADMIN_PASSWD` (Odoo master password), any long random strings. Coolify pre-creates the key
   from the compose file but leaves it empty; fill it in or Postgres refuses to initialize.
4. Domain on the `odoo` service: `https://odoo-proto.<your-domain>` → port 8069.
5. Deploy. First build clones the repos and takes a few minutes.
6. Open the domain, create database `proto` (language Español (AR), country Argentina,
   load demo data: no), master password = the `ADMIN_PASSWD` value.

## Inside Odoo, in this order

1. Apps → install `l10n_ar_fiscal_ws` (ARCA connection + electronic invoicing; at 19.0 this
   single module replaces the old `l10n_ar_afipws` + `l10n_ar_afipws_fe`). Then `l10n_ar_tax`
   (perceptions/withholdings, pulls `l10n_ar_ux` and the ADHOC accounting deps), `point_of_sale`
   (core `l10n_ar_pos` auto-installs; POS orders are invoiced and the invoice goes through
   `l10n_ar_fiscal_ws`), `sale_management`, `stock`, `purchase`.
   Optional: `l10n_ar_fiscal_ws_reports` for the libro IVA exports.
2. Company: CUIT, Responsable Inscripto, IIBB Córdoba, activity start date.
3. Certificate: Ajustes → Facturación → ARCA → homologación. Without a certificate the module
   validates locally in homologación, so steps 4-7 and the non-CAE tests can start right away.
   Upload `pcp.crt` and `pcp.key` (see below) when the ARCA paperwork is done.
4. Fiscal Points: one journal per point of sale: `0001` Depósito (WSFE), `0002` Local A, `0003` Local B.
5. Warehouses: Depósito, Local A, Local B. One POS config per local, bound to its journal.
6. Price lists: Minorista, Mayorista, Especial (warehouse only), "Mayorista -14%".
7. Products: a ream (unit, packaging "Caja x10" with its own barcode), a sleeve of cups.

## Acceptance tests

- Factura B (consumidor final) from Local A's POS → CAE returned.
- Factura A to a Responsable Inscripto from a backend sale invoiced under 0001.
- Cross-location sale: order at Local A, warehouse `Depósito`, stock reserved there, delivery validated → invoice under 0002.
- Supplier bill with IVA 21% plus a Córdoba IIBB perception line.
- Nota de crédito on the Factura A → CAE returned.
- Stock Transfer Depósito → Local A in two steps, in-transit visible.

## ARCA homologación certificate

Needs the company's CUIT with clave fiscal (or a test CUIT of the accountant). Steps:

```bash
mkdir -p certs && cd certs
openssl genrsa -out pcp.key 2048
openssl req -new -key pcp.key -subj "/C=AR/O=PCP Prototype/CN=pcp-proto/serialNumber=CUIT 20XXXXXXXXX" -out pcp.csr
```

Upload `pcp.csr` in ARCA → "WSASS - Autogestión Certificados Homologación" → Nuevo certificado.
Download the `.crt`. Then in the same WSASS screen, "Crear autorización a servicio" for
alias `pcp-proto` → service `wsfe`. Keep `pcp.key` out of git (already ignored).
