from .common import PricingCase


class TestReplacementCost(PricingCase):
    def test_a_receipt_sets_the_cost_from_the_discounted_price_plus_freight(self):
        self.receive(self.ream, 10, price=200, discount=10)
        self.assertAlmostEqual(self.ream.replacement_cost, 189)  # 200 × 0.90 × 1.05

    def test_the_last_purchase_replaces_the_cost_never_averaged(self):
        self.receive(self.ream, 100, price=200)
        self.receive(self.ream, 1, price=300)
        self.assertAlmostEqual(self.ream.replacement_cost, 315)

    def test_a_purchase_in_packs_gives_the_cost_of_one_unit(self):
        self.receive(self.ream, 2, price=1000, uom=self.box)
        self.assertAlmostEqual(self.ream.replacement_cost, 105)

    def test_editing_a_received_purchase_leaves_the_cost_alone(self):
        order = self.receive(self.ream, 10, price=200)
        order.order_line.price_unit = 400
        self.assertAlmostEqual(self.ream.replacement_cost, 210)

    def test_a_warehouse_user_can_receive_and_the_cost_still_moves(self):
        clerk = self.env["res.users"].create(
            {
                "name": "Depósito",
                "login": "deposito",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id, self.env.ref("stock.group_stock_user").id])],
            }
        )
        self.receive(self.ream, 10, price=200, user=clerk)
        self.assertAlmostEqual(self.ream.replacement_cost, 210)

    def test_iva_included_in_the_purchase_price_is_left_out_of_the_cost(self):
        iva_included = self.env["account.tax"].create(
            {
                "name": "IVA 21% incl. (test)",
                "amount": 21,
                "type_tax_use": "purchase",
                "price_include_override": "tax_included",
            }
        )
        self.receive(self.ream, 10, price=121, taxes=iva_included)
        self.assertAlmostEqual(self.ream.replacement_cost, 105)  # 121 / 1.21 × 1.05

    def test_the_cost_keeps_the_decimals_of_a_sub_cent_price(self):
        self.receive(self.ream, 1000, price=0.0345)
        self.assertAlmostEqual(self.ream.replacement_cost, 0.036225)

    def test_a_free_bonus_line_leaves_the_cost_of_the_paid_one(self):
        self.receive(self.ream, 10, price=200, bonus=1)
        self.assertAlmostEqual(self.ream.replacement_cost, 210)

    def test_a_negative_price_line_leaves_the_cost_alone(self):
        self.receive(self.ream, 10, price=200)
        self.receive(self.ream, 1, price=-50)  # a supplier credit booked as a stock line
        self.assertAlmostEqual(self.ream.replacement_cost, 210)

    def test_each_variant_keeps_the_cost_of_its_own_last_purchase(self):
        small, large = self.bag_variants()
        self.receive(small, 100, price=10)
        self.receive(large, 100, price=30)
        self.assertAlmostEqual(small.replacement_cost, 10.5)
        self.assertAlmostEqual(large.replacement_cost, 31.5)
        self.assertAlmostEqual(self.wholesale_list._get_product_price(small, 1), 16.275)  # 10.5 × 1.55

    def test_a_new_cost_moves_the_price_lists(self):
        self.receive(self.ream, 10, price=200)
        self.assertAlmostEqual(self.wholesale_list._get_product_price(self.ream, 1), 325.5)  # 210 × 1.55
