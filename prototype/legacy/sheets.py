"""Spreadsheets the client edits in Google Sheets, with the standard library only.

Sheets in a Spanish locale reads `1130,694` from a CSV as one thousand and more, and writes it back as
`1,130,694`. An .xlsx carries numbers as numbers, so it goes out as .xlsx; what comes back may be the
.xlsx or a CSV export (`,` and no BOM from Sheets, `;` with a BOM from the first round's files).
"""

import csv
import io
import re
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree
from xml.sax.saxutils import escape

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
# A fixed timestamp: the same rows give the same bytes.
EPOCH = (1980, 1, 1, 0, 0, 0)
# XML 1.0 refuses these even escaped; the old system's descriptions may hold them.
ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")

OFFICE = "application/vnd.openxmlformats-officedocument.spreadsheetml"
CONTENT_TYPES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\
<Default Extension="xml" ContentType="application/xml"/>\
<Override PartName="/xl/workbook.xml" ContentType="{OFFICE}.sheet.main+xml"/>\
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{OFFICE}.worksheet+xml"/>\
<Override PartName="/xl/styles.xml" ContentType="{OFFICE}.styles+xml"/>\
</Types>"""
ROOT_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{RELS}">\
<Relationship Id="rId1" Type="{DOC_RELS}/officeDocument" Target="xl/workbook.xml"/></Relationships>"""
WORKBOOK_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{RELS}">\
<Relationship Id="rId1" Type="{DOC_RELS}/worksheet" Target="worksheets/sheet1.xml"/>\
<Relationship Id="rId2" Type="{DOC_RELS}/styles" Target="styles.xml"/></Relationships>"""
# Style 1 is the bold header.
STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="{MAIN}">\
<fonts count="2"><font><sz val="10"/><name val="Arial"/></font>\
<font><b/><sz val="10"/><name val="Arial"/></font></fonts>\
<fills count="2"><fill><patternFill patternType="none"/></fill>\
<fill><patternFill patternType="gray125"/></fill></fills>\
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>\
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>\
<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>\
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>\
</styleSheet>"""


def column_name(index):
    """0 -> A, 25 -> Z, 26 -> AA."""
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name


def column_index(name):
    index = 0
    for c in name:
        index = index * 26 + ord(c) - 64
    return index - 1


def _cell(ref, value, style=0):
    s = f' s="{style}"' if style else ""
    if isinstance(value, bool) or value is None or value == "":
        return ""
    if isinstance(value, int | float):
        number = int(value) if float(value).is_integer() else value
        return f'<c r="{ref}"{s}><v>{number!r}</v></c>'
    text = escape(ILLEGAL.sub("", str(value)))
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def write_xlsx(path, sheet, header, rows):
    """One sheet: a bold, frozen, filterable header, then the rows. Numbers become numeric cells, the
    rest text, so a code like `001446` keeps its zeros. Refuses to overwrite `path`."""
    rows = [list(r) for r in rows]
    last = f"{column_name(len(header) - 1)}{len(rows) + 1}"
    widths = [min(60, max(len(str(v)) for v in [h, *(r[i] for r in rows[:2000])]) + 2) for i, h in enumerate(header)]
    out = io.StringIO()
    out.write(f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="{MAIN}">')
    out.write(
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
    )
    out.write("<cols>")
    for i, width in enumerate(widths, 1):
        out.write(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>')
    out.write("</cols><sheetData>")
    for r, values in enumerate([header, *rows], 1):
        style = 1 if r == 1 else 0
        cells = "".join(_cell(f"{column_name(c)}{r}", v, style) for c, v in enumerate(values))
        out.write(f'<row r="{r}">{cells}</row>')
    out.write(f'</sheetData><autoFilter ref="A1:{last}"/></worksheet>')
    workbook = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<workbook xmlns="{MAIN}" xmlns:r="{DOC_RELS}"><sheets>'
        f'<sheet name="{escape(sheet)}" sheetId="1" r:id="rId1"/></sheets>'
        f'<definedNames><definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">'
        f"'{escape(sheet)}'!$A$1:${last.rstrip('0123456789')}${len(rows) + 1}</definedName></definedNames>"
        f"</workbook>"
    )
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "xl/workbook.xml": workbook,
        "xl/_rels/workbook.xml.rels": WORKBOOK_RELS,
        "xl/styles.xml": STYLES,
        "xl/worksheets/sheet1.xml": out.getvalue(),
    }
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED) as z:
        for name, text in parts.items():
            z.writestr(zipfile.ZipInfo(name, EPOCH), text.encode("utf-8"), zipfile.ZIP_DEFLATED)


def read_table(path):
    """The rows of a spreadsheet as dicts by header, every value a string; blank rows are skipped."""
    path = str(path)
    if path.lower().endswith(".xlsx"):
        rows = _read_xlsx(path)
    else:
        with open(path, encoding="utf-8-sig", newline="") as f:
            text = f.read()
        first = text.split("\n", 1)[0]
        delimiter = ";" if first.count(";") > first.count(",") else ","
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    if not rows:
        return []
    header = [h.strip() for h in rows[0]]
    return [
        dict(zip(header, [*r, *[""] * (len(header) - len(r))], strict=False))
        for r in rows[1:]
        if any(v.strip() for v in r)
    ]


def _read_xlsx(path):
    """The first sheet's cells as text: shared strings (what Sheets writes), inline strings and numbers."""
    ns = {"m": MAIN}
    with zipfile.ZipFile(path) as z:
        workbook = ElementTree.fromstring(z.read("xl/workbook.xml"))
        first = workbook.find("m:sheets/m:sheet", ns).get(f"{{{DOC_RELS}}}id")
        rels = ElementTree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = next(r.get("Target") for r in rels if r.get("Id") == first)
        sheet = target.lstrip("/") if target.startswith("/") else str(PurePosixPath("xl") / target)
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{{{MAIN}}}t")) for si in root.findall("m:si", ns)]
        data = ElementTree.fromstring(z.read(sheet))
    rows = []
    for row in data.iterfind("m:sheetData/m:row", ns):
        values = {}
        for c in row.findall("m:c", ns):
            kind, v = c.get("t"), c.find("m:v", ns)
            if kind == "s":
                text = shared[int(v.text)]
            elif kind == "inlineStr":
                text = "".join(t.text or "" for t in c.iter(f"{{{MAIN}}}t"))
            else:
                text = v.text if v is not None and v.text else ""
            values[column_index(re.match(r"[A-Z]+", c.get("r")).group())] = text
        r = int(row.get("r", len(rows) + 1))
        rows.extend([] for _ in range(r - 1 - len(rows)))
        rows.append([values.get(i, "") for i in range(max(values, default=-1) + 1)])
    return rows
