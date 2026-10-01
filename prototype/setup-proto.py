#!/usr/bin/env python3
"""Configure the prototype instance over XML-RPC. Idempotent: reruns update, never duplicate.

Reads .env.proto-secrets. Placeholder CUITs pass the checksum but belong to nobody;
replace the company CUIT with the real one before connecting to ARCA.
"""
import os, sys, xmlrpc.client
from pathlib import Path

for line in (Path(__file__).parent / ".env.proto-secrets").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k, v)
URL, DB, PW = os.environ["ODOO_URL"], os.environ["ODOO_DB"], os.environ["ODOO_ADMIN_PASSWORD"]
uid = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common").authenticate(DB, "admin", PW, {})
_m = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

def call(model, meth, *a, **k): return _m.execute_kw(DB, uid, PW, model, meth, list(a), k)
def create(model, vals, **k):
    """Odoo 19 create takes a list. Some addons override create without @api.model_create_multi,
    which makes the RPC layer consume the first argument as record ids; retry with a dummy ids list."""
    try:
        return call(model, "create", [vals], **k)[0]
    except xmlrpc.client.Fault as e:
        if "missing 1 required positional argument: 'vals_list'" not in e.faultString: raise
        r = call(model, "create", [], [vals], **k); return r[0] if isinstance(r, list) else r
def one(model, domain, **k):
    ids = call(model, "search", domain, limit=1, **k); return ids[0] if ids else None
def upsert(model, domain, vals, ctx=None):
    k = {"context": ctx} if ctx else {}
    rid = one(model, domain, **k)
    if rid:
        cur = call(model, "read", [rid], fields=list(vals), **k)[0]
        def same(a, b): return (a[0] if isinstance(a, list) and len(a) == 2 and isinstance(a[0], int) else a) == b
        diff = {f: v for f, v in vals.items() if not same(cur.get(f), v)}
        if diff: call(model, "write", [rid], diff, **k)
        print(f"  = {model} {rid}" + (f" updated {sorted(diff)}" if diff else ""))
    else: rid = create(model, vals, **k); print(f"  + {model} {rid}")
    return rid
def cuit_check(base10):
    w = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]; r = 11 - sum(int(d) * x for d, x in zip(base10, w)) % 11
    return {11: "0", 10: "9"}.get(r, str(r))
def cuit(prefix, num8): b = f"{prefix}{num8:08d}"; return b + cuit_check(b)

RI, CF = 1, 5                      # responsibility types
CUIT_TYPE, DNI_TYPE = 4, 5         # identification types
TAX_S21, TAX_P21 = 64, 65
TAX_P_IIBB_CBA = 4
UNIT = 1
WSFE = one("l10n_ar.fiscal.ws", [["code", "=", "wsfe"]])
# FISCAL_WS=1 once the homologación certificate is loaded. Until then the journals number locally
# as preprinted: l10n_ar_fiscal_ws asks ARCA for the last number before its own local-validation
# fallback can apply, so without a certificate WSFE journals cannot post at all.
FISCAL_WS = os.environ.get("FISCAL_WS", "0") == "1"

print(":: company")
company_cuit = os.environ.get("COMPANY_CUIT") or cuit("30", 71000001)
call("res.company", "write", [1], {
    "name": "PCP Prototipo SA",
    "l10n_ar_afip_responsibility_type_id": RI,
    "l10n_ar_gross_income_type": "local",
    "l10n_ar_gross_income_number": "280-00000-0",
    "l10n_ar_afip_start_date": "2015-01-01",
})
call("res.partner", "write", [1], {"vat": company_cuit, "l10n_latam_identification_type_id": CUIT_TYPE,
                                   "city": "Córdoba", "state_id": one("res.country.state", [["code", "=", "X"], ["country_id.code", "=", "AR"]]),
                                   "street": "Av. Colón 1000", "zip": "5000"})
print(f"  company CUIT {company_cuit}")

print(":: settings: homologación, pricelists, line discounts, UoM/packagings, multi-warehouse")
sid = create("res.config.settings", {"l10n_ar_fiscal_ws_env_type": "homologation", "group_product_pricelist": True,
                                     "group_discount_per_so_line": True, "group_uom": True,
                                     "group_stock_multi_locations": True, "group_stock_adv_location": True})
try: call("res.config.settings", "execute", [sid])
except xmlrpc.client.Fault as e:
    if "cannot marshal None" not in e.faultString: raise

print(":: warehouses")  # DEP resupplies the stores; stores can also resupply each other
wh = {}
wh["DEP"] = upsert("stock.warehouse", [["code", "in", ["WH", "DEP"]]], {"name": "Depósito", "code": "DEP"})
wh["LOCC"] = upsert("stock.warehouse", [["code", "=", "LOCC"]], {"name": "Local Centro", "code": "LOCC"})
wh["LOCN"] = upsert("stock.warehouse", [["code", "=", "LOCN"]], {"name": "Local Norte", "code": "LOCN"})
call("stock.warehouse", "write", [wh["LOCC"]], {"resupply_wh_ids": [[6, 0, [wh["DEP"], wh["LOCN"]]]]})
call("stock.warehouse", "write", [wh["LOCN"]], {"resupply_wh_ids": [[6, 0, [wh["DEP"], wh["LOCC"]]]]})
whrec = {k: call("stock.warehouse", "read", [v], fields=["pos_type_id", "lot_stock_id"])[0] for k, v in wh.items()}

print(":: internal consumption: one location, one operation type per warehouse")
consume_loc = upsert("stock.location", [["name", "=", "Consumo interno"], ["usage", "=", "inventory"]],
                     {"name": "Consumo interno", "usage": "inventory"})
for code, wid in wh.items():
    upsert("stock.picking.type", [["name", "=", "Consumo interno"], ["warehouse_id", "=", wid]],
           {"name": "Consumo interno", "code": "internal", "sequence_code": "CONS", "warehouse_id": wid,
            "default_location_src_id": whrec[code]["lot_stock_id"][0], "default_location_dest_id": consume_loc,
            "show_operations": False})

print(":: fiscal points (WSFE journals)")
jr = {}
base = one("account.journal", [["type", "=", "sale"], ["l10n_ar_afip_pos_number", "=", 1]])
for code, num, name in [("DEP", 1, "Depósito"), ("LOCC", 2, "Local Centro"), ("LOCN", 3, "Local Norte")]:
    vals = {"name": f"Ventas {name} (PV {num:04d})", "type": "sale", "code": f"V{num:03d}",
            "l10n_latam_use_documents": True, "l10n_ar_afip_pos_system": "RAW_MAW" if FISCAL_WS else "II_IM",
            "l10n_ar_afip_pos_number": num, "l10n_ar_afip_pos_partner_id": 1,
            "l10n_ar_fiscal_ws_id": WSFE if FISCAL_WS else False}
    dom = [["id", "=", base]] if (num == 1 and base) else [["type", "=", "sale"], ["l10n_ar_afip_pos_number", "=", num]]
    # A journal with posted invoices cannot change its fiscal setup: retire it and create a fresh one.
    old = one("account.journal", dom + [["l10n_ar_afip_pos_system", "!=", vals["l10n_ar_afip_pos_system"]]])
    if old and call("account.move", "search_count", [["journal_id", "=", old], ["state", "=", "posted"]]):
        drafts = call("account.move", "search", [["journal_id", "=", old], ["state", "=", "draft"]])
        if drafts: call("account.move", "unlink", drafts)
        call("account.journal", "write", [old], {"name": f"Ventas {name} (retirado {old})", "code": f"X{old:03d}"[:5], "active": False})
        print(f"  - account.journal {old} retired")
        dom = [["type", "=", "sale"], ["l10n_ar_afip_pos_number", "=", num]]
    jr[code] = upsert("account.journal", dom, vals)

print(":: price lists")
pl = {}
for name in ["Minorista", "Mayorista", "Especial"]:
    pl[name] = upsert("product.pricelist", [["name", "=", name]], {"name": name, "currency_id": 19})
for stale in call("product.pricelist", "search", [["name", "=", "Predeterminado"]]): call("product.pricelist", "write", [stale], {"active": False})
pl["Mayorista -14%"] = upsert("product.pricelist", [["name", "=", "Mayorista -14%"]], {"name": "Mayorista -14%", "currency_id": 19})
upsert("product.pricelist.item", [["pricelist_id", "=", pl["Mayorista -14%"]], ["applied_on", "=", "3_global"]],
       {"pricelist_id": pl["Mayorista -14%"], "applied_on": "3_global", "compute_price": "percentage",
        "base": "pricelist", "base_pricelist_id": pl["Mayorista"], "percent_price": 14})

print(":: products")  # stock in the smallest unit sold; the box is a packaging UoM with its own barcode
prods = {}
def product(name, barcode, retail, wholesale, special, pack=None):
    tid = upsert("product.template", [["barcode", "=", barcode]], {
        "name": name, "type": "consu", "is_storable": True, "barcode": barcode, "list_price": retail,
        "uom_id": UNIT, "taxes_id": [[6, 0, [TAX_S21]]], "supplier_taxes_id": [[6, 0, [TAX_P21]]]})
    pid = call("product.product", "search", [["product_tmpl_id", "=", tid]])[0]
    for lname, price in [("Minorista", retail), ("Mayorista", wholesale), ("Especial", special)]:
        upsert("product.pricelist.item", [["pricelist_id", "=", pl[lname]], ["product_tmpl_id", "=", tid]],
               {"pricelist_id": pl[lname], "applied_on": "1_product", "product_tmpl_id": tid,
                "compute_price": "fixed", "fixed_price": price})
    if pack:
        pname, qty, pbarcode = pack
        uom = upsert("uom.uom", [["name", "=", pname]], {"name": pname, "relative_uom_id": UNIT, "relative_factor": qty})
        call("product.template", "write", [tid], {"uom_ids": [[4, uom]]})
        upsert("product.uom", [["product_id", "=", pid], ["uom_id", "=", uom]], {"product_id": pid, "uom_id": uom, "barcode": pbarcode})
    prods[name] = (tid, pid); return tid, pid
product("Resma A4 75g", "7790001000011", 9500, 7600, 7000, pack=("Caja x10 resmas", 10, "17790001000018"))
product("Vasos plásticos 180cc x50", "7790002000028", 3200, 2500, 2300, pack=("Bolsa x20 paquetes", 20, "17790002000025"))
product("Bolígrafo azul", "7790003000035", 450, 320, 290, pack=("Caja x50 bolígrafos", 50, "17790003000032"))

print(":: partners")
upsert("res.partner", [["vat", "=", cuit("30", 71000002)]], {
    "name": "Distribuidora Rivera SRL", "is_company": True, "vat": cuit("30", 71000002),
    "l10n_latam_identification_type_id": CUIT_TYPE, "l10n_ar_afip_responsibility_type_id": RI,
    "property_product_pricelist": pl["Mayorista -14%"], "customer_rank": 1})
upsert("res.partner", [["vat", "=", "30123456"]], {
    "name": "Juana Pérez", "vat": "30123456", "l10n_latam_identification_type_id": DNI_TYPE,
    "l10n_ar_afip_responsibility_type_id": CF, "property_product_pricelist": pl["Minorista"], "customer_rank": 1})
sup = upsert("res.partner", [["vat", "=", cuit("30", 71000003)]], {
    "name": "Papelera del Centro SA", "is_company": True, "vat": cuit("30", 71000003),
    "l10n_latam_identification_type_id": CUIT_TYPE, "l10n_ar_afip_responsibility_type_id": RI, "supplier_rank": 1})
upsert("l10n_ar.partner.tax", [["partner_id", "=", sup], ["tax_id", "=", TAX_P_IIBB_CBA]],
       {"partner_id": sup, "tax_id": TAX_P_IIBB_CBA})

print(":: points of sale")
for code, name in [("LOCC", "Caja Local Centro"), ("LOCN", "Caja Local Norte"), ("DEP", "Caja Depósito")]:
    avail = [pl["Minorista"], pl["Mayorista"], pl["Mayorista -14%"]] + ([pl["Especial"]] if code == "DEP" else [])
    upsert("pos.config", [["name", "=", name]], {
        "name": name, "picking_type_id": whrec[code]["pos_type_id"][0], "invoice_journal_id": jr[code],
        "use_pricelist": True, "pricelist_id": pl["Minorista"], "available_pricelist_ids": [[6, 0, avail]],
        "manual_discount": True})

print("done")
