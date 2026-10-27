import csv
import tempfile
import unittest
from pathlib import Path

from catalog_review import group_variants, match_catalogs, read_products, write_review


def product(code, description, branch="01", category="100", cost=10.0, vat=21.0, pack=1.0, supplier="00310"):
    from catalog_review import Product

    return Product(branch, code, description, category, "Bolsas", cost, (0.0, 0.0, 0.0, 0.0), vat, pack, supplier)


def grouped(groups):
    return [sorted(g.values) for g in groups]


class GroupVariantsTest(unittest.TestCase):
    def test_colours_of_one_product_are_one_group(self):
        groups = group_variants(
            [
                product("100001", "Bolsa Camiseta 30x40 Roja"),
                product("100002", "Bolsa Camiseta 30x40 Azul"),
                product("100003", "Bolsa Camiseta 30x40 Verde agua"),
            ]
        )
        self.assertEqual(grouped(groups), [["100001", "100002", "100003"]])
        g = groups[0]
        self.assertEqual((g.name, g.attribute, g.confidence), ("Bolsa Camiseta 30x40", "Color", "Alta"))
        self.assertEqual(g.values, {"100001": "Rojo", "100002": "Azul", "100003": "Verde agua"})

    def test_sizes_are_a_measure_group(self):
        groups = group_variants(
            [product("100001", "Bolsa Riñon 20x30", cost=5), product("100002", "Bolsa Riñon 25x35")]
        )
        self.assertEqual((groups[0].name, groups[0].attribute), ("Bolsa Riñon", "Medida"))
        self.assertEqual(groups[0].values, {"100001": "20x30", "100002": "25x35"})
        self.assertIn("costos distintos", groups[0].reason)

    def test_capacity_and_weight_name_their_attribute(self):
        capacity = group_variants([product("1", "Botella Aceite 250cc"), product("2", "Botella Aceite 500 cc")])
        weight = group_variants([product("3", "Banda Elastica 50 Grs"), product("4", "Banda Elastica 1 Kg")])
        self.assertEqual((capacity[0].attribute, weight[0].attribute), ("Capacidad", "Peso"))

    def test_never_mixes_categories_or_vat_rates(self):
        groups = group_variants(
            [
                product("1", "Bolsa Camiseta Roja"),
                product("2", "Bolsa Camiseta Azul", category="200"),
                product("3", "Bolsa Camiseta Verde", vat=10.5),
            ]
        )
        self.assertEqual(groups, [])

    def test_identical_descriptions_are_not_variants(self):
        groups = group_variants(
            [
                product("1", "Bowl 750ml Compostable"),
                product("2", "Bowl 750ml Compostable"),
                product("3", "Bowl 500ml Compostable"),
            ]
        )
        self.assertEqual(grouped(groups), [["1", "3"]])

    def test_a_code_joins_one_group_and_colour_wins(self):
        groups = group_variants(
            [
                product("1", "Vaso 180cc Rojo"),
                product("2", "Vaso 180cc Azul"),
                product("3", "Vaso 300cc Rojo", supplier="00999"),
            ]
        )
        codes = [c for g in groups for c in g.values]
        self.assertEqual(sorted(codes), sorted(set(codes)))
        self.assertEqual(groups[0].attribute, "Color")

    def test_colour_groups_differing_in_a_measure_are_one_product(self):
        groups = group_variants(
            [
                product("1", "Bolsa Manija Blanca 22x30x10"),
                product("2", "Bolsa Manija Kraft 22x30x10"),
                product("3", "Bolsa Manija Blanca 26x36x12"),
                product("4", "Bolsa Manija Kraft 26x36x12"),
            ]
        )
        self.assertEqual(grouped(groups), [["1", "2", "3", "4"]])
        g = groups[0]
        self.assertEqual((g.name, g.attribute, g.attribute2), ("Bolsa Manija", "Color", "Medida"))
        self.assertEqual(g.values2, {"1": "22x30x10", "2": "22x30x10", "3": "26x36x12", "4": "26x36x12"})

    def test_the_name_drops_the_varying_token_not_the_same_digits_elsewhere(self):
        groups = group_variants([product("1", "Cinta 48x50 48"), product("2", "Cinta 48x50 60")])
        self.assertEqual(groups[0].name, "Cinta 48x50")

    def test_a_different_word_is_a_model_group_with_lower_confidence(self):
        groups = group_variants([product("1", "Juego de Mesa Ludo", cost=1), product("2", "Juego de Mesa Oca", cost=2)])
        self.assertEqual((groups[0].attribute, groups[0].confidence), ("Modelo", "Baja"))


class MatchCatalogsTest(unittest.TestCase):
    def test_same_words_in_another_case_and_order_match_with_high_confidence(self):
        matches = match_catalogs(
            [product("100001", "Rollo Termico 76x50")], [product("5", "ROLLO 76X50 TÉRMICO", branch="03", cost=4)]
        )
        self.assertEqual([(m.warehouse.code, m.alberdi.code, m.confidence) for m in matches], [("100001", "5", "Alta")])

    def test_different_measures_never_match(self):
        matches = match_catalogs(
            [product("100001", "Rollo Termico 76x50")], [product("5", "ROLLO TERMICO 76X40", branch="03")]
        )
        self.assertEqual(matches, [])

    def test_each_side_keeps_only_its_most_similar(self):
        matches = match_catalogs(
            [product("100001", "Blond Calada 21x27"), product("100002", "Blond Calada Oro 21x27")],
            [product("5", "BLOND CALADAS 21X27", branch="03")],
        )
        self.assertEqual([(m.warehouse.code, m.alberdi.code) for m in matches], [("100001", "5")])
        self.assertIn("abreviaturas", matches[0].reason)

    def test_a_repeated_word_counts_once_so_similarity_never_passes_100(self):
        matches = match_catalogs([product("100001", "Bolsa Bolsa Roja")], [product("6", "BOLSA ROJA", branch="03")])
        self.assertEqual([(m.alberdi.code, m.score) for m in matches], [("6", 1.0)])

    def test_unrelated_descriptions_do_not_match(self):
        matches = match_catalogs(
            [product("100001", "Bolsa Carbon x3kg")], [product("5", "CARBONILLA ARTISTICA", branch="03")]
        )
        self.assertEqual(matches, [])


class WriteReviewTest(unittest.TestCase):
    def test_every_warehouse_code_is_a_row_of_a_spreadsheet_friendly_csv(self):
        dump = (
            "COD_SUC\tCOD_PRO\tDET_PRO\tCOD_RUB\tRUBRO\tPRE_CTO\tBONIF1\tBONIF2\tBONIF3\tBONIF4\tIVA\tUNIBUL\tCUENTAP\n"
            "01\t100001\tCinta Pack 48x50mts Marrón\t110\tCintas\t1860.5\t20\t0\t0\t0\t21\t36\t00310\n"
            "01\t100002\tCinta Pack 48x50mts Cristal\t110\tCintas\t1860.5\t20\t0\t0\t0\t21\t36\t00310\n"
            "01\t100003\tTalonario\\tRifa\t296\tNULL\t448\t0\t0\t0\t0\t21\t0\t00939\n"
            "03\t000001\tCINTA PACK 48X50MTS MARRON\t576\tCINTAS ENGOMADAS\t12\t0\t0\t0\t0\t21\t0\t00760\n"
        )
        with tempfile.TemporaryDirectory() as out:
            write_review(read_products(dump.splitlines(keepends=True)), Path(out))
            raw = (Path(out) / "variantes_deposito.csv").read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines(), delimiter=";"))
            duplicates = (Path(out) / "duplicados_deposito_alberdi.csv").read_text(encoding="utf-8-sig")
        self.assertEqual([r["codigo"] for r in rows], ["100001", "100002", "100003"])
        self.assertEqual(rows[0]["costo"], "1860,5")
        self.assertEqual(rows[0]["bonificaciones"], "20%")
        self.assertEqual((rows[0]["grupo"], rows[0]["atributo"], rows[0]["valor"]), ("1", "Color", "Marrón"))
        self.assertEqual(rows[0]["duplicado_en_alberdi"], "000001 CINTA PACK 48X50MTS MARRON")
        self.assertEqual((rows[2]["descripcion"], rows[2]["rubro"], rows[2]["grupo"]), ("Talonario\tRifa", "296", ""))
        self.assertIn("100001;Cinta Pack 48x50mts Marrón", duplicates)


if __name__ == "__main__":
    unittest.main()
