from .common import PricingCase


class TestPriceLists(PricingCase):
    def test_lists_add_the_category_margin_to_the_cost_then_iva(self):
        self.assertAlmostEqual(self.price_with_iva(self.wholesale_list, self.ream), 187.55)
        self.assertAlmostEqual(self.price_with_iva(self.retail_list, self.ream), 266.20)

    def test_a_new_cost_or_margin_moves_the_price(self):
        self.ream.replacement_cost = 200
        self.assertAlmostEqual(self.wholesale_list._get_product_price(self.ream, 1), 310)
        self.category.retail_margin = 100
        self.assertAlmostEqual(self.retail_list._get_product_price(self.ream, 1), 400)

    def test_the_price_is_never_rounded(self):
        self.ream.replacement_cost = 33.33
        self.assertAlmostEqual(self.wholesale_list._get_product_price(self.ream, 1), 51.6615)

    def test_the_pack_unit_is_priced_as_its_units(self):
        self.assertAlmostEqual(self.wholesale_list._get_product_price(self.ream, 1, uom=self.box), 1550)
