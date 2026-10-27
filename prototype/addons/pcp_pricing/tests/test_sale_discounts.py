from .common import PricingCase


class TestSaleDiscounts(PricingCase):
    def test_a_wholesale_loose_unit_gets_the_customer_discount(self):
        line = self.sell(self.wholesale_customer, 1)
        self.assertEqual(line.discount, 14)
        self.assertAlmostEqual(line.price_total, 161.29, places=2)  # 187.55 × 0.86

    def test_a_wholesale_closed_pack_adds_the_pack_discount(self):
        line = self.sell(self.wholesale_customer, 10)
        self.assertEqual(line.discount, 19)
        self.assertAlmostEqual(line.price_total, 1519.16, places=2)  # 10 × 187.55 × 0.81

    def test_several_packs_sold_in_the_pack_unit_get_the_pack_discount(self):
        self.assertEqual(self.sell(self.wholesale_customer, 3, uom=self.box).discount, 19)

    def test_a_quantity_between_packs_gets_only_the_customer_discount(self):
        self.assertEqual(self.sell(self.wholesale_customer, 15).discount, 14)

    def test_a_packaging_alone_does_not_give_the_pack_discount(self):
        self.ream.pack_size = 0
        self.assertEqual(self.sell(self.wholesale_customer, 10).discount, 14)

    def test_each_variant_has_its_own_pack_size(self):
        small, large = self.bag_variants()
        small.write({"pack_size": 1000, "replacement_cost": 10})
        large.write({"pack_size": 500, "replacement_cost": 10})
        self.assertEqual(self.sell(self.wholesale_customer, 1000, product=small).discount, 19)
        self.assertEqual(self.sell(self.wholesale_customer, 500, product=small).discount, 14)
        self.assertEqual(self.sell(self.wholesale_customer, 1500, product=large).discount, 19)

    def test_a_single_variant_product_takes_its_pack_size_from_the_product_form(self):
        pens = self.env["product.template"].create(
            {"name": "Bolígrafo", "categ_id": self.category.id, "replacement_cost": 1, "pack_size": 50}
        )
        self.assertEqual(self.sell(self.wholesale_customer, 100, product=pens.product_variant_id).discount, 19)

    def test_a_retail_customer_never_gets_a_discount_even_on_a_pack(self):
        line = self.sell(self.retail_customer, 10)
        self.assertEqual(line.discount, 0)
        self.assertAlmostEqual(line.price_total, 2662.0, places=2)

    def test_a_contact_buys_with_its_company_s_customer_discount(self):
        contact = self.env["res.partner"].create({"name": "Compras", "parent_id": self.wholesale_customer.id})
        self.assertEqual(self.sell(contact, 1).discount, 14)

    def test_changing_the_quantity_to_a_pack_moves_the_discount(self):
        line = self.sell(self.wholesale_customer, 1)
        line.product_uom_qty = 20
        self.assertEqual(line.discount, 19)

    def test_a_down_payment_is_not_discounted(self):
        order = self.sell(self.wholesale_customer, 10).order_id
        order.action_confirm()
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_model="sale.order", active_ids=order.ids)
            .create({"advance_payment_method": "fixed", "fixed_amount": 1000})
        )
        wizard.create_invoices()
        down_payment = order.order_line.filtered(lambda ln: ln.is_downpayment and not ln.display_type)
        self.assertEqual(down_payment.discount, 0)

    def test_the_invoice_keeps_the_line_discount(self):
        line = self.sell(self.wholesale_customer, 10)
        line.order_id.action_confirm()
        line.qty_delivered = 10
        invoice = line.order_id._create_invoices()
        self.assertEqual(invoice.invoice_line_ids.discount, 19)
