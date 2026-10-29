from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

from .common import PricingFixtures


@tagged("post_install", "-at_install")
class TestPosDiscounts(PricingFixtures, TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_pricing()
        cls.main_pos_config.write(
            {
                "use_pricelist": True,
                "pricelist_id": cls.retail_list.id,
                "available_pricelist_ids": [(6, 0, (cls.retail_list | cls.wholesale_list).ids)],
            }
        )

    def test_the_till_prices_from_the_lists_and_discounts_wholesale_lines(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("pcp_pricing_pos_discounts")
        orders = self.main_pos_config.current_session_id.order_ids.sorted("id")
        self.assertEqual(len(orders), 3)
        wholesale_pack, wholesale_loose, retail_pack = (o.lines for o in orders)
        self.assertEqual((wholesale_pack.qty, wholesale_pack.discount), (10, 19))
        self.assertAlmostEqual(wholesale_pack.price_subtotal_incl, 1519.16, places=2)  # 10 × 187.55 × 0.81
        self.assertEqual((wholesale_loose.qty, wholesale_loose.discount), (1, 14))
        self.assertAlmostEqual(wholesale_loose.price_subtotal_incl, 161.29, places=2)  # 187.55 × 0.86
        self.assertEqual((retail_pack.qty, retail_pack.discount), (10, 0))
        self.assertAlmostEqual(retail_pack.price_subtotal_incl, 2662.0, places=2)  # 10 × 266.20
