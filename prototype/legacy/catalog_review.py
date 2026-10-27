#!/usr/bin/env python3
"""Propose the catalog review of #26 from the old system's products.

Reads the tab-separated output of `catalog.sql` (as `uv run just legacy-sql` prints it) on stdin and
writes two CSVs and a note, in Spanish, to the directory given as argument:

- `variantes_deposito.csv`: every active Warehouse (01) code, with the variant group proposed for it.
- `duplicados_deposito_alberdi.csv`: the proposed matches between a Warehouse and an Alberdi (03) code.

Deterministic: the same database gives the same files. Nothing here talks to Odoo.
"""

import csv
import math
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

WAREHOUSE, ALBERDI = "01", "03"

# The client opens these in a Spanish-locale Excel or LibreOffice: `;` separates, `,` is the decimal mark.
DELIMITER = ";"
OUTPUTS = ("variantes_deposito.csv", "duplicados_deposito_alberdi.csv")

# Colour words and their abbreviations, by the value they stand for (masculine: "negra" is Negro).
COLOURS = {
    "amarillo": "Amarillo",
    "amarilla": "Amarillo",
    "azul": "Azul",
    "beige": "Beige",
    "blanco": "Blanco",
    "blanca": "Blanco",
    "bco": "Blanco",
    "bca": "Blanco",
    "bordo": "Bordó",
    "celeste": "Celeste",
    "celes": "Celeste",
    "crema": "Crema",
    "cristal": "Cristal",
    "crist": "Cristal",
    "dorado": "Dorado",
    "dorada": "Dorado",
    "fucsia": "Fucsia",
    "gris": "Gris",
    "lila": "Lila",
    "marron": "Marrón",
    "naranja": "Naranja",
    "negro": "Negro",
    "negra": "Negro",
    "neg": "Negro",
    "oro": "Oro",
    "plata": "Plata",
    "plateado": "Plateado",
    "plateada": "Plateado",
    "rojo": "Rojo",
    "roja": "Rojo",
    "rosa": "Rosa",
    "rosado": "Rosado",
    "rosada": "Rosado",
    "transparente": "Transparente",
    "turquesa": "Turquesa",
    "verde": "Verde",
    "vde": "Verde",
    "violeta": "Violeta",
    "natural": "Natural",
    "multicolor": "Multicolor",
    "salmon": "Salmón",
    "bronce": "Bronce",
    "cobre": "Cobre",
    "magenta": "Magenta",
    "habano": "Habano",
    "kraft": "Kraft",
    "marfil": "Marfil",
    "lavanda": "Lavanda",
    "chocolate": "Chocolate",
}
# Two-word colours are one value: "verde agua" is not "verde" plus a word.
COMPOUND_COLOURS = (
    "verde agua",
    "verde manzana",
    "verde oscuro",
    "verde claro",
    "azul francia",
    "azul marino",
    "rosa chicle",
    "rosa pastel",
    "celeste pastel",
    "amarillo pastel",
    "verde pastel",
    "lila pastel",
    "rojo fuego",
    "azul oscuro",
    "azul claro",
)

UNITS = {
    "cc": "cc",
    "ml": "ml",
    "l": "l",
    "lt": "l",
    "lts": "l",
    "litro": "l",
    "litros": "l",
    "kg": "kg",
    "kgs": "kg",
    "kilo": "kg",
    "g": "g",
    "gr": "g",
    "grs": "g",
    "cm": "cm",
    "cms": "cm",
    "mm": "mm",
    "m": "m",
    "mt": "m",
    "mts": "m",
    "metro": "m",
    "metros": "m",
    "mic": "mic",
    "micrones": "mic",
    "micras": "mic",
    "u": "u",
    "un": "u",
    "uni": "u",
    "unid": "u",
    "unidades": "u",
    "hojas": "h",
    "hjs": "h",
    "h": "h",
    "w": "w",
    "v": "v",
    "nro": "nro",
}
CAPACITY_UNITS, WEIGHT_UNITS = {"cc", "ml", "l"}, {"kg", "g"}
STOPWORDS = {"de", "del", "con", "c", "p", "para", "el", "la", "los", "las", "y", "en", "a", "por", "s", "al"}

NUM = r"\d+(?:[.,]\d+)?"
UNIT = "|".join(sorted(UNITS, key=len, reverse=True))
TOKEN = re.compile(
    rf"(?P<dim>{NUM}(?:\s*[x*]\s*{NUM})+(?:\s*(?:{UNIT})(?![a-z]))?)"
    rf"|(?P<qty>(?<![a-z])x\s*{NUM}(?:\s*(?:{UNIT})(?![a-z]))?)"
    rf"|(?P<numunit>{NUM}\s*(?:{UNIT})(?![a-z]))"
    rf"|(?P<num>{NUM})"
    r"|(?P<word>[a-z]+)"
)


@dataclass(frozen=True)
class Product:
    branch: str
    code: str
    description: str
    category: str
    category_name: str
    cost: float
    discounts: tuple
    vat: float
    pack: float
    supplier: str


@dataclass
class Token:
    kind: str  # dim, qty, numunit, num, word or colour
    key: str  # what is compared
    text: str  # as written in the description
    start: int = 0  # where the text sits in the description


@dataclass
class Group:
    number: int
    name: str
    attribute: str
    values: dict  # code -> value
    confidence: str
    reason: str
    members: list = field(default_factory=list)
    attribute2: str = ""
    values2: dict = field(default_factory=dict)  # code -> value of the second attribute


@dataclass
class Match:
    warehouse: Product
    alberdi: Product
    score: float
    confidence: str
    reason: str


@dataclass
class _Candidate:
    products: list
    position: int
    tokens: dict = field(default_factory=dict)


def fold(text):
    """Lowercase without accents, one character for one, so spans map back to the original text."""
    return "".join(unicodedata.normalize("NFKD", c)[0].lower() for c in text)


def tokenize(description):
    folded = fold(description)
    for compound in COMPOUND_COLOURS:
        folded = re.sub(rf"\b{compound}\b", compound.replace(" ", "_"), folded)
    tokens = []
    for m in re.finditer(rf"(?P<compound>[a-z]+_[a-z]+)|{TOKEN.pattern}", folded):
        span = description[m.start() : m.end()]
        text = span.strip()
        start = m.start() + len(span) - len(span.lstrip())
        kind = m.lastgroup
        raw = m.group(kind)
        if kind == "compound":
            tokens.append(Token("colour", raw.replace("_", " "), text, start))
        elif kind == "word":
            if raw in COLOURS:
                tokens.append(Token("colour", COLOURS[raw].lower(), text, start))
            elif raw not in STOPWORDS:
                tokens.append(Token("word", raw, text, start))
        else:
            key = re.sub(r"\s+", "", raw).replace(",", ".").replace("*", "x")
            unit = re.search(r"[a-z]+$", key)
            if unit:
                key = key[: unit.start()] + UNITS.get(unit.group(), unit.group())
            tokens.append(Token(kind, key, text, start))
    return tokens


def numbers(tokens):
    return {float(n) for t in tokens if t.kind != "word" for n in re.findall(r"\d+(?:\.\d+)?", t.key)}


def attribute_of(kinds):
    """Name the attribute that the varying tokens of a group express."""
    if kinds == {"colour"}:
        return "Color"
    if kinds <= {"dim", "qty", "numunit", "num"}:
        if kinds == {"qty"}:
            return "Cantidad"
        return "Medida"
    return "Modelo"


def _refine_measure(tokens):
    units = {re.sub(r"^[\dx.]+", "", t.key) for t in tokens if t.kind in {"numunit", "qty"}}
    if units and units <= CAPACITY_UNITS:
        return "Capacidad"
    if units and units <= WEIGHT_UNITS:
        return "Peso"
    return None


def _same(values, tolerance=0.0):
    values = list(values)
    return all(abs(v - values[0]) <= tolerance * max(abs(values[0]), 1e-9) for v in values)


def group_variants(products):
    """Propose variant groups: codes whose descriptions differ in one token, in one category and IVA rate.

    Odoo keeps the category and the taxes on the Product, not on the variant, so a group never mixes
    them. A code joins one group at most; colour groups are preferred, then measures, then the rest.
    """
    tokenized = {p.code: tokenize(p.description) for p in products}
    by_key = defaultdict(lambda: _Candidate([], 0))
    for p in products:
        tokens = tokenized[p.code]
        if len(tokens) < 2:
            continue
        for i, token in enumerate(tokens):
            pattern = tuple(t.key for t in tokens[:i]) + ("*",) + tuple(t.key for t in tokens[i + 1 :])
            candidate = by_key[(p.category, p.vat, pattern)]
            candidate.position = i
            candidate.products.append(p)
            candidate.tokens[p.code] = token

    rank = {"Color": 0, "Medida": 1, "Cantidad": 1, "Modelo": 2}

    def order(candidate):
        kinds = {t.kind for t in candidate.tokens.values()}
        return (rank[attribute_of(kinds)], -len(candidate.products), min(p.code for p in candidate.products))

    candidates = [c for c in by_key.values() if len({t.key for t in c.tokens.values()}) > 1]
    taken, groups = set(), []
    for candidate in sorted(candidates, key=order):
        # One code per value: two codes with the same description stay out, they are a duplicate, not a variant.
        members, seen = [], set()
        for p in sorted(candidate.products, key=lambda p: p.code):
            key = candidate.tokens[p.code].key
            if p.code not in taken and key not in seen:
                members.append(p)
                seen.add(key)
        if len(members) < 2:
            continue
        taken.update(p.code for p in members)
        groups.append(_make_group(len(groups) + 1, members, candidate, tokenized))
    groups = _merge_by_measure(groups)
    for number, group in enumerate(groups, 1):
        group.number = number
    return groups


def _merge_by_measure(groups):
    """One Product with two attributes: colour groups whose names differ only in a measure."""
    measures = {"dim", "qty", "numunit", "num"}
    by_key = defaultdict(list)
    for group in groups:
        if group.attribute != "Color":
            continue
        first = group.members[0]
        tokens = tokenize(group.name)
        for i, token in enumerate(tokens):
            if token.kind in measures:
                pattern = tuple(t.key for t in tokens[:i]) + ("*",) + tuple(t.key for t in tokens[i + 1 :])
                by_key[(first.category, first.vat, pattern)].append((group, token))
    merged, result = set(), []
    for key in sorted(by_key, key=lambda k: -len(by_key[k])):
        parts = [(g, t) for g, t in by_key[key] if id(g) not in merged]
        if len({t.key for _, t in parts}) < 2:
            continue
        merged.update(id(g) for g, _ in parts)
        result.append(_combine(parts))
    result.extend(g for g in groups if id(g) not in merged)
    return result


def _combine(parts):
    groups = [g for g, _ in parts]
    first, token = parts[0]
    name = _without(first.name, token)
    members = [p for g in groups for p in g.members]
    values2 = {p.code: _value(t) for g, t in parts for p in g.members}
    colours = sorted({v for g in groups for v in g.values.values()})
    measures = list(dict.fromkeys(values2.values()))
    order = ["Alta", "Media", "Baja"]
    confidence = max((g.confidence for g in groups), key=order.index)
    checks = [
        f"misma descripción salvo color ({' / '.join(colours)}) y medida ({' / '.join(measures)})",
        "mismo rubro e IVA",
        "en cada medida, mismo costo por color"
        if all("mismo costo" in g.reason for g in groups)
        else "costos distintos entre colores de una medida",
        "mismo proveedor" if len({p.supplier for p in members}) == 1 else "proveedores distintos",
        "misma unidad de bulto" if _same(p.pack for p in members) else "unidades de bulto distintas",
    ]
    values = {code: v for g in groups for code, v in g.values.items()}
    return Group(0, name, "Color", values, confidence, "; ".join(checks), members, "Medida", values2)


def _make_group(number, members, candidate, tokenized):
    tokens = [candidate.tokens[p.code] for p in members]
    kinds = {t.kind for t in tokens}
    attribute = attribute_of(kinds)
    if attribute == "Medida":
        attribute = _refine_measure(tokens) or attribute
    first = tokenized[members[0].code][candidate.position]
    name = _without(members[0].description, first)
    values = {p.code: _value(t) for p, t in zip(members, tokens, strict=True)}

    same_cost = _same((p.cost for p in members), 0.005) and _same(sum(p.discounts) for p in members)
    same_pack = _same(p.pack for p in members)
    same_supplier = len({p.supplier for p in members}) == 1
    checks = [
        f"misma descripción salvo {attribute.lower()} ({' / '.join(values.values())})",
        "mismo rubro e IVA",
        "mismo costo" if same_cost else "costos distintos",
        "mismo proveedor" if same_supplier else "proveedores distintos",
        "misma unidad de bulto" if same_pack else "unidades de bulto distintas",
    ]
    if attribute == "Modelo":
        confidence = "Media" if same_cost and same_supplier else "Baja"
    elif attribute == "Color":
        confidence = "Alta" if same_cost and same_supplier else "Media"
    elif attribute == "Cantidad":
        # Units per pack may be a packaging of one product rather than a variant: the client decides.
        confidence = "Media"
    else:
        confidence = "Alta" if same_supplier else "Media"
    return Group(number, name, attribute, values, confidence, "; ".join(checks), members)


def _without(text, token):
    """The text without the token, cut by its position: the same characters may appear elsewhere in it."""
    return _clean_name(text[: token.start] + " " + text[token.start + len(token.text) :])


def _clean_name(name):
    name = re.sub(r"\(\s*\)", " ", name)
    name = re.sub(r"\s+([/.,)])", r"\1", name)
    return re.sub(r"\s{2,}", " ", name).strip(" -/.,")


def _value(token):
    text = token.key if token.kind == "colour" else token.text.strip(" -/.,")
    return text[:1].upper() + text[1:]


def match_catalogs(warehouse, alberdi):
    """Propose Warehouse/Alberdi pairs that look like one item: each the other's most similar description.

    Costs are not compared: Alberdi's are years old for many items. Measures must agree: two descriptions
    that name different numbers are never a match.
    """
    w_tokens = {p.code: _match_keys(p.description) for p in warehouse}
    a_tokens = {p.code: _match_keys(p.description) for p in alberdi}
    score = _scorer([*w_tokens.values(), *a_tokens.values()])
    index = defaultdict(set)
    for p in alberdi:
        for key in a_tokens[p.code]:
            index[key[:4]].add(p)

    best_for_w, best_for_a = {}, defaultdict(lambda: (0.0, ""))
    for w in warehouse:
        w_numbers = numbers(tokenize(w.description))
        scored = [
            (score(w_tokens[w.code], a_tokens[a.code]), a.code, a)
            for a in {a for key in w_tokens[w.code] for a in index[key[:4]]}
            # Different measures, or a measure on one side only, are different items.
            if numbers(tokenize(a.description)) == w_numbers
        ]
        if not scored:
            continue
        best_for_w[w.code] = max(scored, key=lambda s: s[:2])
        for s, code, _a in scored:
            best_for_a[code] = max(best_for_a[code], (s, w.code))

    return [
        _describe_match(w, a, s, w_tokens[w.code], a_tokens[a.code])
        for w in warehouse
        if w.code in best_for_w
        for s, code, a in [best_for_w[w.code]]
        if s >= 0.5 and best_for_a[code][1] == w.code
    ]


def _scorer(documents):
    """Weighted overlap of two descriptions' words: a rare word that both share counts more than a common one."""
    document_frequency = defaultdict(int)
    for keys in documents:
        for key in set(keys):
            document_frequency[key] += 1
    idf = {k: math.log(1 + len(documents) / n) for k, n in document_frequency.items()}

    def score(left, right):
        matched = sum(max((_soft_equal(key, other) for other in right), default=0) * idf[key] for key in left)
        union = sum(idf[k] for k in left) + sum(idf[k] for k in right) - matched
        return matched / union if union else 0.0

    return score


def _describe_match(w, a, s, w_keys, a_keys):
    same_words = sorted(w_keys) == sorted(a_keys)
    same_category = fold(w.category_name).strip() == fold(a.category_name).strip() != ""
    if same_words:
        confidence = "Alta"
    elif s >= 0.75 or (s >= 0.6 and same_category):
        confidence = "Media"
    else:
        confidence = "Baja"
    reasons = [
        "misma descripción (sin mayúsculas, acentos ni signos)" if same_words else f"descripción parecida ({s:.0%})"
    ]
    reasons.append("mismos números y medidas" if numbers(tokenize(w.description)) else "ninguna menciona números")
    if not same_words:
        only_w = [t.text for t in tokenize(w.description) if not _covered(t.key, a_keys)]
        only_a = [t.text for t in tokenize(a.description) if not _covered(t.key, w_keys)]
        if only_w or only_a:
            reasons.append(f"palabras distintas: {' '.join(only_w) or '-'} / {' '.join(only_a) or '-'}")
        else:
            reasons.append("difieren solo en abreviaturas, plurales u orden")
    if same_category:
        reasons.append("rubro del mismo nombre")
    if w.vat != a.vat:
        reasons.append(f"IVA distinto ({_number(w.vat)} / {_number(a.vat)})")
    return Match(w, a, s, confidence, "; ".join(reasons))


def _match_keys(description):
    """Each word once: a word repeated on one side must not count twice against one on the other."""
    return list(dict.fromkeys(t.key for t in tokenize(description)))


def _covered(key, keys):
    return any(_soft_equal(key, other) for other in keys)


def _soft_equal(a, b):
    """Same key, or an abbreviation of a word: `bol` for `bolsa`, `cris` for `cristal`."""
    if a == b:
        return 1.0
    if a.isalpha() and b.isalpha() and min(len(a), len(b)) >= 3 and (a.startswith(b) or b.startswith(a)):
        return 0.8
    return 0.0


def read_products(lines):
    reader = csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE)
    header = next(reader)
    products = []
    for row in reader:
        r = dict(zip(header, (_unescape(v) for v in row), strict=True))
        products.append(
            Product(
                branch=r["COD_SUC"],
                code=r["COD_PRO"],
                description=(r["DET_PRO"] or "").strip(),
                category=r["COD_RUB"] or "",
                category_name=r["RUBRO"] or "",
                cost=float(r["PRE_CTO"] or 0),
                discounts=tuple(float(r[f"BONIF{i}"] or 0) for i in range(1, 5)),
                vat=float(r["IVA"] or 0),
                pack=float(r["UNIBUL"] or 0),
                supplier=r["CUENTAP"] or "",
            )
        )
    return products


def _unescape(value):
    """mysql --batch writes NULL as `NULL` and escapes tab, newline and backslash."""
    if value == "NULL":
        return None
    return re.sub(r"\\(.)", lambda m: {"t": "\t", "n": "\n", "0": "\0"}.get(m.group(1), m.group(1)), value)


def _number(value):
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", ",")


def _discounts(product):
    return " + ".join(f"{_number(d)}%" for d in product.discounts if d)


def write_review(products, out):
    warehouse = [p for p in products if p.branch == WAREHOUSE]
    alberdi = [p for p in products if p.branch == ALBERDI]
    groups = group_variants(warehouse)
    matches = match_catalogs(warehouse, alberdi)
    group_of = {code: g for g in groups for code in g.values}
    match_of = {m.warehouse.code: m for m in matches}
    confidence_order = {"Alta": 0, "Media": 1, "Baja": 2}

    def variant_order(p):
        g = group_of.get(p.code)
        return (0, confidence_order[g.confidence], g.number, p.code) if g else (1, 0, 0, p.code)

    with open(out / OUTPUTS[0], "x", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=DELIMITER)
        w.writerow(
            [
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
                "duplicado_en_alberdi",
                "confirmado",
            ]
        )
        for p in sorted(warehouse, key=variant_order):
            g = group_of.get(p.code)
            m = match_of.get(p.code)
            w.writerow(
                [
                    p.code,
                    p.description,
                    f"{p.category} {p.category_name}".strip(),
                    _number(p.cost),
                    _discounts(p),
                    _number(p.vat),
                    _number(p.pack),
                    p.supplier,
                    g.number if g else "",
                    g.name if g else "",
                    g.attribute if g else "",
                    g.values[p.code] if g else "",
                    g.attribute2 if g else "",
                    g.values2.get(p.code, "") if g else "",
                    g.confidence if g else "",
                    g.reason if g else "",
                    f"{m.alberdi.code} {m.alberdi.description}" if m else "",
                    "",
                ]
            )

    with open(out / OUTPUTS[1], "x", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=DELIMITER)
        w.writerow(
            [
                "codigo_deposito",
                "descripcion_deposito",
                "rubro_deposito",
                "codigo_alberdi",
                "descripcion_alberdi",
                "rubro_alberdi",
                "costo_deposito",
                "costo_alberdi",
                "similitud",
                "confianza",
                "motivo",
                "confirmado",
            ]
        )
        for m in sorted(matches, key=lambda m: (confidence_order[m.confidence], -m.score, m.warehouse.code)):
            w.writerow(
                [
                    m.warehouse.code,
                    m.warehouse.description,
                    f"{m.warehouse.category} {m.warehouse.category_name}".strip(),
                    m.alberdi.code,
                    m.alberdi.description,
                    f"{m.alberdi.category} {m.alberdi.category_name}".strip(),
                    _number(m.warehouse.cost),
                    _number(m.alberdi.cost),
                    f"{m.score:.0%}",
                    m.confidence,
                    m.reason,
                    "",
                ]
            )
    return warehouse, groups, matches


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: catalog_review.py <out-dir>  (reads catalog.sql's output on stdin)")
    out = Path(sys.argv[1])
    # The client fills these files in: a rerun into the same directory must not wipe their answers.
    existing = [name for name in (*OUTPUTS, "LEEME.txt") if (out / name).exists()]
    if existing:
        sys.exit(f"{out} already has {', '.join(existing)}: move them away or pick another directory")
    out.mkdir(parents=True, exist_ok=True)
    products = read_products(sys.stdin)
    warehouse, groups, matches = write_review(products, out)
    note = Path(__file__).with_name("LEEME.txt")
    (out / "LEEME.txt").write_text(note.read_text(encoding="utf-8"), encoding="utf-8")

    def by_confidence(items):
        counts = defaultdict(int)
        for item in items:
            counts[item.confidence] += 1
        return ", ".join(f"{c} {counts[c]}" for c in ("Alta", "Media", "Baja"))

    print(f"{len(warehouse)} Warehouse codes, {sum(p.branch == ALBERDI for p in products)} Alberdi codes")
    print(f"{len(groups)} groups ({by_confidence(groups)}), {sum(len(g.values) for g in groups)} codes in groups")
    print(f"{len(matches)} matches ({by_confidence(matches)})")
    print(f"written to {out}")


if __name__ == "__main__":
    main()
