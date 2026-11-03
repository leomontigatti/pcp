#!/usr/bin/env python3
"""Second round of the catalog review (#26): Brasil and Alberdi in one file.

The client revised the Brasil (01) proposal of `catalog_review.py` and wants to group variants seeing
every brand at once, and Brasil sells its stationery with Alberdi's (03) codes. This reads catalog.sql's
output on stdin and the client's revised `variantes_deposito` (Google Sheets' CSV export, the first
round's `;` CSV, or an .xlsx) named as the first argument, and writes to the directory named second:

- `catalogo_combinado.xlsx`: every Brasil row of the revised file, with the client's edits verbatim
  and the old system's numbers, then every live Alberdi code: a proposed duplicate of a Brasil code
  sits under it, ungrouped; the rest join a Brasil group when only the variant word differs, or get
  groups of their own. Sorted by category, then group.
- `alberdi_sin_actividad.xlsx`: the Alberdi codes with no activity in the backup, for the client to
  say which are still sold.

Deterministic, and never touches Odoo.
"""

import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# python3 -I leaves the script's directory off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_review import (  # noqa: E402
    ALBERDI,
    WAREHOUSE,
    _discounts,
    fold,
    group_variants,
    match_catalogs,
    read_products,
    tokenize,
)
from sheets import read_table, write_xlsx  # noqa: E402

OUTPUTS = ("catalogo_combinado.xlsx", "alberdi_sin_actividad.xlsx", "LEEME.txt")
COLUMNS = [
    "sucursal",
    "codigo",
    "descripcion",
    "rubro",
    "costo",
    "bonificaciones",
    "iva",
    "unidades_bulto",
    "proveedor",
    "grupo",
    "producto_propuesto",
    "atributo",
    "valor",
    "atributo_2",
    "valor_2",
    "confianza",
    "motivo",
    "duplicado_de",
    "confirmado",
]
INACTIVE_COLUMNS = [
    "codigo",
    "descripcion",
    "rubro",
    "costo",
    "bonificaciones",
    "iva",
    "ultimo_aumento",
    "ultima_modificacion",
    "duplicado_de",
    "se_sigue_vendiendo",
]
# The client's columns: kept as they wrote them. The old system's columns are never taken from the
# sheet, whose locale turned `1130,694` into `1,130,694`.
CLIENT_COLUMNS = (
    "descripcion",
    "grupo",
    "producto_propuesto",
    "atributo",
    "valor",
    "atributo_2",
    "valor_2",
    "confianza",
    "motivo",
    "confirmado",
)
SYSTEM_COLUMNS = ("rubro", "costo", "bonificaciones", "iva", "unidades_bulto", "proveedor")
NO_CODE = "ARTÍCULO NUEVO, sin código del sistema viejo: rubro, costo e IVA copiados de la planilla, revisarlos"
UNKNOWN_CODE = "CÓDIGO NO ENCONTRADO entre los activos de Brasil: datos copiados de la planilla, revisarlos"
BARE_NUMBER = "un valor es un número sin unidad: puede ser una medida o un número de artículo (otro modelo)"
MEASURES = {"dim", "qty", "numunit", "num", "paper"}
UNIT_NAMES = {"h": "hojas"}


@dataclass
class Row:
    values: dict
    branch: str
    code: str
    group: int | None = None
    order: tuple = ()  # (category key, group, branch, position): the sheet's sort order
    duplicates: list = field(default_factory=list)  # Alberdi rows shown right under this one


@dataclass
class Result:
    rows: list
    inactive: list
    renumbered: dict  # the client's letter groups -> the numbers they got
    joined: int  # Alberdi codes added to a Brasil group
    new_groups: int
    alberdi_in_new_groups: int
    duplicates: int
    dropped: list  # Brasil codes in the database, missing from the revised file


def group_label(value):
    """A group as written: `283`, `283.0` from an .xlsx number, or letters; empty for none."""
    value = (value or "").strip()
    return re.sub(r"^(\d+)\.0+$", r"\1", value)


def renumber_groups(labels):
    """Free numbers for the groups the client named with letters (`aaa`, `???`; case matters).

    First the unused numbers up to the highest numeric group, lowest first, then past it; the letters
    take them in the order they first appear.
    """
    labels = [group_label(v) for v in labels]
    used = {int(v) for v in labels if v.isdigit()}
    letters = list(dict.fromkeys(v for v in labels if v and not v.isdigit()))
    free = [n for n in range(1, max(used, default=0) + 1) if n not in used]
    free += range(max(used, default=0) + 1, max(used, default=0) + 1 + len(letters))
    return dict(zip(letters, free, strict=False))


def normalized_value(text):
    """An attribute value with its unit, the way #27 asks: `250 cc`, `15 x 21 cm`, `60 g`, `10 u`."""
    tokens = tokenize(text)
    if len(tokens) != 1 or tokens[0].kind not in MEASURES | {"colour"}:
        return text
    token = tokens[0]
    if token.kind == "colour":
        return token.key[:1].upper() + token.key[1:]
    m = re.fullmatch(r"(x?)([\d.]+(?:x[\d.]+)*)([a-z]*)", token.key)
    if not m:
        return text
    count, figures, unit = m.groups()
    unit = UNIT_NAMES.get(unit, unit) or ("u" if count else "")
    return f"{figures.replace('.', ',').replace('x', ' x ')} {unit}".strip()


def _category(product):
    return f"{product.category} {product.category_name}".strip()


def _category_key(product):
    if product is None:
        return ("", "")
    return (fold(product.category_name).strip(), product.category)


def _system_values(product):
    return {
        "rubro": _category(product),
        "costo": product.cost,
        "bonificaciones": _discounts(product),
        "iva": product.vat,
        "unidades_bulto": product.pack,
        "proveedor": product.supplier,
    }


def brasil_rows(revised, warehouse):
    """The revised rows, with the client's columns verbatim and the system's from the database."""
    by_code = {p.code: p for p in warehouse}
    renumbered = renumber_groups(r.get("grupo") for r in revised)
    rows = []
    for position, r in enumerate(revised):
        code = (r.get("codigo") or "").strip()
        values = {c: (r.get(c) or "") for c in CLIENT_COLUMNS}
        label = group_label(r.get("grupo"))
        group = int(label) if label.isdigit() else renumbered.get(label)
        values["grupo"] = group if group is not None else ""
        product = by_code.get(code)
        if product:
            values.update(_system_values(product))
        else:
            values.update({c: (r.get(c) or "") for c in SYSTEM_COLUMNS})
            flag = NO_CODE if not code else UNKNOWN_CODE
            values["motivo"] = f"{flag}; {values['motivo']}" if values["motivo"] else flag
        values.update(sucursal="Brasil", codigo=code, duplicado_de="")
        rows.append(Row(values, WAREHOUSE, code, group, (position,)))
    return rows, renumbered


def _pattern(tokens, i):
    return tuple(t.key for t in tokens[:i]) + ("*",) + tuple(t.key for t in tokens[i + 1 :])


def _bare_number(value):
    tokens = tokenize(value)
    return len(tokens) == 1 and tokens[0].kind == "num"


def _shape(token):
    """What a value must share with the group's to be one more of them: `1 kg` is no plate size `20`."""
    return token.kind, re.sub(r"^[\dx.]+", "", token.key) if token.kind in {"dim", "qty", "numunit"} else ""


def _group_axes(rows, products):
    """Where each Brasil group varies: {(vat, pattern): {group: tokens in the gap}}, and each group's attribute."""
    by_code = {p.code: p for p in products}
    members = defaultdict(list)
    for row in rows:
        if row.group is not None:
            members[row.group].append(row)
    axes = defaultdict(lambda: defaultdict(list))
    attributes = {}
    for number, group_rows in members.items():
        rates = {by_code[r.code].vat for r in group_rows if r.code in by_code}
        attribute = group_rows[0].values["atributo"].strip()
        if len(rates) != 1 or not attribute or any(r.values["atributo_2"].strip() for r in group_rows):
            continue
        (vat,) = rates
        attributes[number] = attribute
        for r in group_rows:
            tokens = tokenize(r.values["descripcion"])
            if sum(t.kind == "word" for t in tokens) < 2:
                continue
            for i, token in enumerate(tokens):
                if token.kind != "word":
                    axes[(vat, _pattern(tokens, i))][number].append(token)
    # A gap is the group's axis only when two of its members differ there, in values of one shape.
    axes = {
        key: {n: ts for n, ts in by_group.items() if len({t.key for t in ts}) > 1 and len({_shape(t) for t in ts}) == 1}
        for key, by_group in axes.items()
    }
    return axes, attributes


def join_brasil_groups(rows, products, alberdi):
    """Alberdi codes that are one more variant of a Brasil group: {code: (group, attribute, value, reason)}.

    Only when the description is a Brasil member's in every word but the one the group varies in,
    and that one is a colour or a measure: a different word may be another brand. The group must
    have one IVA rate, one attribute and at least two words besides the variant (the product and
    something that names it, usually the brand). Ante la duda, no agrupar: an Alberdi code that fits
    two groups joins none.
    """
    axes, groups = _group_axes(rows, products)
    taken = defaultdict(set)  # group -> value keys already in it
    for by_group in axes.values():
        for n, ts in by_group.items():
            taken[n].update(t.key for t in ts)
    joined = {}
    for p in sorted(alberdi, key=lambda p: p.code):
        tokens = tokenize(p.description)
        fits = {}
        for i, token in enumerate(tokens):
            for n, ts in axes.get((p.vat, _pattern(tokens, i)), {}).items():
                if _shape(ts[0]) == _shape(token) and token.key not in taken[n]:
                    fits[n] = token
        if len(fits) != 1:
            continue
        ((n, token),) = fits.items()
        taken[n].add(token.key)
        value = normalized_value(token.text)
        reason = (
            f"misma descripción que el grupo {n} de Brasil salvo {groups[n].lower()} ({value}); mismo IVA; "
            "el costo de Alberdi puede estar desactualizado"
        )
        joined[p.code] = (n, groups[n], value, reason)
    return joined


def _alberdi_values(product, **values):
    return {
        **dict.fromkeys(COLUMNS, ""),
        **_system_values(product),
        "sucursal": "Alberdi",
        "codigo": product.code,
        "descripcion": product.description,
        **values,
    }


def _new_groups(alberdi, first_new):
    """Alberdi's own variant groups, numbered past `first_new`, as rows for every code given."""
    # A Modelo group varies in a word: in Alberdi that is often the brand (EZCO / PELIKAN) or the pack
    # (X50 / C/U), and a group holds one brand and one pack size. Ante la duda, no agrupar.
    groups = [g for g in group_variants(alberdi) if g.attribute != "Modelo"]
    for number, g in enumerate(groups, 1):
        g.number = number
        if any(_bare_number(v) for v in [*g.values.values(), *g.values2.values()]):
            g.confidence = "Baja"
            g.reason = f"{BARE_NUMBER}; {g.reason}"
    group_of = {code: g for g in groups for code in g.values}
    rows = []
    for p in alberdi:
        g = group_of.get(p.code)
        if not g:
            rows.append(Row(_alberdi_values(p), ALBERDI, p.code))
            continue
        n = first_new + g.number
        values = _alberdi_values(
            p,
            grupo=n,
            producto_propuesto=g.name,
            atributo=g.attribute,
            valor=normalized_value(g.values[p.code]),
            atributo_2=g.attribute2,
            valor_2=normalized_value(g.values2[p.code]) if p.code in g.values2 else "",
            confianza=g.confidence,
            motivo=g.reason,
        )
        rows.append(Row(values, ALBERDI, p.code, n))
    return rows, groups


def _sorted_rows(brasil, alberdi, by_code):
    """By category, then group, Brasil before Alberdi; each duplicate right under its Brasil row."""
    # A group sorts under the category of its first Brasil row, or of its first code.
    anchor = {}
    for r in [*brasil, *sorted(alberdi, key=lambda r: r.code)]:
        if r.group is not None and r.code in by_code:
            anchor.setdefault(r.group, by_code[r.code])
    branch_order = {WAREHOUSE: 0, ALBERDI: 1}
    for r in [*brasil, *alberdi]:
        position = r.order[0] if r.order else r.code
        category = _category_key(anchor.get(r.group) if r.group is not None else by_code.get(r.code))
        r.order = (category, r.group if r.group is not None else math.inf, branch_order[r.branch], position)
    ordered = []
    for r in sorted([*brasil, *alberdi], key=lambda r: r.order):
        ordered.append(r)
        ordered.extend(r.duplicates)
    return ordered


def build(revised, products):
    warehouse = [p for p in products if p.branch == WAREHOUSE]
    alberdi = [p for p in products if p.branch == ALBERDI]
    rows, renumbered = brasil_rows(revised, warehouse)
    revised_codes = {r.code for r in rows if r.code}
    kept = [p for p in warehouse if p.code in revised_codes]
    dropped = sorted(p.code for p in warehouse if p.code not in revised_codes)
    by_code = {p.code: p for p in products}

    duplicate_of = {m.alberdi.code: m for m in match_catalogs(kept, alberdi)}
    rows_by_code = {r.code: r for r in rows if r.code}
    for code, m in sorted(duplicate_of.items()):
        if not m.alberdi.live:
            continue
        reason = f"parece el mismo artículo que {m.warehouse.code} {m.warehouse.description}: {m.reason}"
        values = _alberdi_values(m.alberdi, confianza=m.confidence, motivo=reason, duplicado_de=m.warehouse.code)
        rows_by_code[m.warehouse.code].duplicates.append(Row(values, ALBERDI, code))

    candidates = [p for p in alberdi if p.live and p.code not in duplicate_of]
    joined = join_brasil_groups(rows, products, candidates)
    alberdi_rows = []
    for p in candidates:
        if p.code in joined:
            n, attribute, value, reason = joined[p.code]
            values = _alberdi_values(p, grupo=n, atributo=attribute, valor=value, confianza="Media", motivo=reason)
            alberdi_rows.append(Row(values, ALBERDI, p.code, n))
    first_new = max((r.group for r in rows if r.group is not None), default=0)
    remaining = [p for p in candidates if p.code not in joined]
    new_rows, groups = _new_groups(remaining, first_new)
    alberdi_rows += new_rows
    ordered = _sorted_rows(rows, alberdi_rows, by_code)

    inactive = sorted((p for p in alberdi if not p.live), key=lambda p: (_category_key(p), p.code))
    inactive_rows = [
        [
            p.code,
            p.description,
            _category(p),
            p.cost,
            _discounts(p),
            p.vat,
            p.last_increase,
            p.last_change,
            duplicate_of[p.code].warehouse.code if p.code in duplicate_of else "",
            "",
        ]
        for p in inactive
    ]
    return Result(
        rows=ordered,
        inactive=inactive_rows,
        renumbered=renumbered,
        joined=len(joined),
        new_groups=len(groups),
        alberdi_in_new_groups=sum(len(g.values) for g in groups),
        duplicates=sum(len(r.duplicates) for r in rows),
        dropped=dropped,
    )


def write(result, out):
    write_xlsx(out / OUTPUTS[0], "catalogo_combinado", COLUMNS, ([r.values[c] for c in COLUMNS] for r in result.rows))
    write_xlsx(out / OUTPUTS[1], "alberdi_sin_actividad", INACTIVE_COLUMNS, result.inactive)
    note = Path(__file__).with_name("LEEME_combinado.txt")
    with open(out / OUTPUTS[2], "x", encoding="utf-8") as f:
        f.write(note.read_text(encoding="utf-8"))


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: catalog_combined.py <revised file> <out-dir>  (reads catalog.sql's output on stdin)")
    revised, out = Path(sys.argv[1]), Path(sys.argv[2])
    # The client fills these files in: a rerun into the same directory must not wipe their answers.
    existing = [name for name in OUTPUTS if (out / name).exists()]
    if existing:
        sys.exit(f"{out} already has {', '.join(existing)}: move them away or pick another directory")
    result = build(read_table(revised), read_products(sys.stdin))
    out.mkdir(parents=True, exist_ok=True)
    write(result, out)
    brasil = sum(r.branch == WAREHOUSE for r in result.rows)
    print(f"{len(result.rows)} rows: {brasil} Brasil, {len(result.rows) - brasil} Alberdi")
    print(f"Brasil codes in the database left out (not in the revised file): {' '.join(result.dropped) or '-'}")
    print(f"letter groups renumbered: {', '.join(f'{k} -> {v}' for k, v in result.renumbered.items()) or '-'}")
    print(f"{result.duplicates} Alberdi duplicates of a Brasil code, {result.joined} joined Brasil groups")
    print(f"{result.new_groups} new Alberdi groups with {result.alberdi_in_new_groups} codes")
    print(f"{len(result.inactive)} Alberdi codes without activity")
    print(f"written to {out}")


if __name__ == "__main__":
    main()
