import tempfile
import unittest
import zipfile
from pathlib import Path

from catalog_combined import build, normalized_value, renumber_groups
from catalog_review import Product, group_variants
from sheets import read_table, write_xlsx

HEADER = (
    "codigo,descripcion,rubro,costo,bonificaciones,iva,unidades_bulto,proveedor,grupo,producto_propuesto,"
    "atributo,valor,atributo_2,valor_2,confianza,motivo,duplicado_en_alberdi,confirmado"
)


def product(code, description, branch="01", category="100", cost=10.0, vat=21.0, live=True, name="Bolsas"):
    return Product(branch, code, description, category, name, cost, (20.0, 0.0, 0.0, 0.0), vat, 6.0, "00310", live)


def revised(*lines):
    """Rows as Google Sheets exports them: `,`, no BOM, numbers in its locale."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "revisado.csv"
        path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8")
        return read_table(path)


def by_code(result):
    return {r.values["codigo"]: r.values for r in result.rows}


class RenumberGroupsTest(unittest.TestCase):
    def test_letters_take_the_free_numbers_first_then_past_the_highest(self):
        mapping = renumber_groups(["1", "aaa", "3", "XXX", "", "xxx", "aaa", "5", "???"])
        self.assertEqual(mapping, {"aaa": 2, "XXX": 4, "xxx": 6, "???": 7})

    def test_a_number_from_an_xlsx_cell_is_the_same_group(self):
        self.assertEqual(renumber_groups(["2.0", "bbb"]), {"bbb": 1})


class BrasilRowsTest(unittest.TestCase):
    def setUp(self):
        self.products = [
            product("100001", "Cuad Tapa Dura x42 Rojo Potosi", cost=1130.694, category="387", name="Cuadernos"),
            product("100002", "Cuad Tapa Dura x42 Azul Potosi", cost=1130.694, category="387", name="Cuadernos"),
            product("102190", "Cuad Tapa Dura x42 Azul Potosi", category="387", name="Cuadernos"),
            product("100003", "Rollo Termico 57x30", category="120", name="Rollos"),
        ]
        self.rows = revised(
            '100001,Cuad Rayado Rojo,387 Cuadernos,"1,130,694",,21,1,1839,aaa,Cuaderno Potosi,Color,Rojo,,,Alta,'
            "mi nota,,Si",
            '100002,Cuad Rayado Azul,,"1,130,694",,21,1,1839,aaa,Cuaderno Potosi,Color,Azul,,,Alta,,,Si',
            ',Cuad Rose II,,"1,618,765",,,,,aaa,Cuaderno Potosi,Color,Rose II,,,,,,Si',
            "100003,Rollo Termico 57x30,120 Rollos,40,,21,1,00310,2,,,,,,,,,",
        )

    def test_the_clients_columns_stay_verbatim_and_letters_become_free_numbers(self):
        rows = by_code(build(self.rows, self.products))
        self.assertEqual(
            {k: rows["100001"][k] for k in ("descripcion", "producto_propuesto", "valor", "motivo", "confirmado")},
            {
                "descripcion": "Cuad Rayado Rojo",
                "producto_propuesto": "Cuaderno Potosi",
                "valor": "Rojo",
                "motivo": "mi nota",
                "confirmado": "Si",
            },
        )
        self.assertEqual((rows["100001"]["grupo"], rows["100003"]["grupo"]), (1, 2))

    def test_numbers_come_from_the_database_never_from_the_sheet(self):
        row = by_code(build(self.rows, self.products))["100002"]
        self.assertEqual(
            (row["costo"], row["bonificaciones"], row["iva"], row["unidades_bulto"], row["rubro"]),
            (1130.694, "20%", 21.0, 6.0, "387 Cuadernos"),
        )

    def test_codes_the_client_removed_stay_out(self):
        result = build(self.rows, self.products)
        self.assertNotIn("102190", by_code(result))
        self.assertEqual(result.dropped, ["102190"])

    def test_a_row_without_code_keeps_the_clients_text_and_says_so(self):
        result = build(self.rows, self.products)
        (row,) = [r.values for r in result.rows if not r.values["codigo"]]
        self.assertEqual((row["costo"], row["grupo"], row["confirmado"]), ("1,618,765", 1, "Si"))
        self.assertTrue(row["motivo"].startswith("ARTÍCULO NUEVO"))


class AlberdiRowsTest(unittest.TestCase):
    def build(self, alberdi, brasil_lines=(), brasil=()):
        return build(revised(*brasil_lines), [*brasil, *alberdi])

    def test_a_duplicate_sits_under_its_brasil_code_without_a_group(self):
        result = self.build(
            [product("000001", "ROLLO 57X30 TÉRMICO", branch="03", category="576", name="ROLLOS")],
            ["100003,Rollo Termico 57x30,,,,,,,,,,,,,,,,"],
            [product("100003", "Rollo Termico 57x30", category="120", name="Rollos")],
        )
        self.assertEqual([r.values["codigo"] for r in result.rows], ["100003", "000001"])
        dup = result.rows[1].values
        self.assertEqual((dup["sucursal"], dup["duplicado_de"], dup["grupo"]), ("Alberdi", "100003", ""))

    def test_codes_without_activity_go_to_their_own_list(self):
        result = self.build(
            [
                product("000001", "CINTA PAPEL 18MM", branch="03"),
                product("000002", "GLOBO LISO X50", branch="03", live=False),
            ]
        )
        self.assertEqual([r.values["codigo"] for r in result.rows], ["000001"])
        self.assertEqual([r[0] for r in result.inactive], ["000002"])

    def test_another_size_of_a_brasil_group_joins_it(self):
        brasil = [
            product("100587", "Cinta Pla 20mm X50mts lisa"),
            product("100590", "Cinta Pla 25mm X50mts lisa"),
        ]
        lines = [
            "100587,Cinta Pla 20mm X50mts lisa,,,,,,,122,Cinta Pla Lisa,Medida,20 mm,,,,,,",
            "100590,Cinta Pla 25mm X50mts lisa,,,,,,,122,Cinta Pla Lisa,Medida,25 mm,,,,,,",
        ]
        alberdi = [
            product("001251", "CINTA PLA 10MM X50MT LISA", branch="03", category="900"),
            # A weight is not one more width, and a word may be another brand.
            product("001252", "CINTA PLA 1KG X50MT LISA", branch="03", category="900"),
            product("001253", "CINTA PLA ACME X50MT LISA", branch="03", category="900"),
        ]
        result = self.build(alberdi, lines, brasil)
        rows = by_code(result)
        self.assertEqual(
            (rows["001251"]["grupo"], rows["001251"]["atributo"], rows["001251"]["valor"]), (122, "Medida", "10 mm")
        )
        self.assertEqual((rows["001252"]["grupo"], rows["001253"]["grupo"]), ("", ""))
        self.assertEqual(result.joined, 1)
        # Joined rows sort inside the Brasil group.
        self.assertEqual([r.values["codigo"] for r in result.rows][:3], ["100587", "100590", "001251"])

    def test_a_value_the_client_already_gave_the_group_is_not_joined_twice(self):
        brasil = [
            product("100587", "Cinta Pla 20mm X50mts lisa"),
            product("100590", "Cinta Pla 25mm X50mts lisa"),
        ]
        # The client corrected the first row to 10 mm: an Alberdi 10 mm would be a second 10 mm.
        lines = [
            "100587,Cinta Pla 20mm X50mts lisa,,,,,,,122,Cinta Pla Lisa,Medida,10 mm,,,,,,",
            "100590,Cinta Pla 25mm X50mts lisa,,,,,,,122,Cinta Pla Lisa,Medida,25 mm,,,,,,",
        ]
        alberdi = [product("001251", "CINTA PLA 10MM X50MT LISA", branch="03", category="900")]
        result = self.build(alberdi, lines, brasil)
        self.assertEqual(by_code(result)["001251"]["grupo"], "")
        self.assertEqual(result.joined, 0)

    def test_new_groups_number_past_the_clients_and_skip_brand_words(self):
        result = self.build(
            [
                product("000001", "BOLIGRAFO BIC CRISTAL AZUL", branch="03"),
                product("000002", "BOLIGRAFO BIC CRISTAL NEGRO", branch="03"),
                product("000003", "BATERIA 9V DURACELL", branch="03"),
                product("000004", "BATERIA 9V RAYOVAC", branch="03"),
            ],
            ["100003,Rollo,,,,,,,7,,,,,,,,,"],
            [product("100003", "Rollo")],
        )
        rows = by_code(result)
        self.assertEqual((rows["000001"]["grupo"], rows["000002"]["grupo"]), (8, 8))
        self.assertEqual((rows["000003"]["grupo"], rows["000004"]["grupo"]), ("", ""))

    def test_a_number_without_unit_may_be_an_article_number(self):
        result = self.build(
            [
                product("000001", "CRAYON PIZZINI 9512", branch="03"),
                product("000002", "CRAYON PIZZINI 9306", branch="03"),
            ]
        )
        self.assertEqual(by_code(result)["000001"]["confianza"], "Baja")


class ValuesTest(unittest.TestCase):
    def test_values_carry_their_unit(self):
        values = ["250cc", "15X21CM", "X 60 grs", "x10", "48 hjs", "NEGRA", "1,5 lts", "48"]
        self.assertEqual(
            [normalized_value(v) for v in values],
            ["250 cc", "15 x 21 cm", "60 g", "10 u", "48 hojas", "Negro", "1,5 l", "48"],
        )

    def test_a_paper_size_is_one_measure(self):
        groups = group_variants([product("1", "PAPEL VEGETAL A4 90GR"), product("2", "PAPEL VEGETAL A3 90GR")])
        self.assertEqual((groups[0].attribute, groups[0].values), ("Medida", {"1": "A4", "2": "A3"}))


class SheetsTest(unittest.TestCase):
    def test_reads_the_first_rounds_csv_and_the_sheets_export(self):
        with tempfile.TemporaryDirectory() as d:
            first = Path(d) / "a.csv"
            first.write_text("codigo;costo\n000001;1130,694\n;\n", encoding="utf-8-sig")
            sheets = Path(d) / "b.csv"
            sheets.write_text('codigo,costo\n000001,"1,130,694"\n', encoding="utf-8")
            self.assertEqual(read_table(first), [{"codigo": "000001", "costo": "1130,694"}])
            self.assertEqual(read_table(sheets), [{"codigo": "000001", "costo": "1,130,694"}])

    def test_xlsx_keeps_numbers_as_numbers_and_codes_as_text(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.xlsx"
            write_xlsx(
                path, "hoja", ["codigo", "costo", "grupo", "descripcion"], [["001446", 1130.694, 12, "A & B\x01"]]
            )
            sheet = zipfile.ZipFile(path).read("xl/worksheets/sheet1.xml").decode()
            self.assertIn("<v>1130.694</v>", sheet)
            self.assertIn('t="inlineStr"><is><t xml:space="preserve">001446</t>', sheet)
            self.assertEqual(
                read_table(path), [{"codigo": "001446", "costo": "1130.694", "grupo": "12", "descripcion": "A & B"}]
            )
            with self.assertRaises(FileExistsError):
                write_xlsx(path, "hoja", ["x"], [])

    def test_reads_shared_strings_and_skipped_cells_as_sheets_writes_them(self):
        main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        rels = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "d.xlsx"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr(
                    "xl/workbook.xml",
                    f'<workbook xmlns="{main}" xmlns:r="{rels}"><sheets><sheet name="x" sheetId="1" r:id="rId3"/>'
                    "</sheets></workbook>",
                )
                z.writestr(
                    "xl/_rels/workbook.xml.rels",
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId3" Target="worksheets/sheet7.xml"/></Relationships>',
                )
                z.writestr(
                    "xl/sharedStrings.xml",
                    f'<sst xmlns="{main}"><si><t>codigo</t></si><si><t>grupo</t></si><si><r><t>Sí</t></r></si></sst>',
                )
                z.writestr(
                    "xl/worksheets/sheet7.xml",
                    f'<worksheet xmlns="{main}"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c>'
                    '<c r="C1" t="s"><v>1</v></c></row><row r="3"><c r="C3"><v>283</v></c>'
                    '<c r="D3" t="s"><v>2</v></c></row></sheetData></worksheet>',
                )
            self.assertEqual(read_table(path), [{"codigo": "", "": "", "grupo": "283"}])


if __name__ == "__main__":
    unittest.main()
