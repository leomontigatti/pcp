from odoo.tests import TransactionCase


class PricingFixtures:
    """A Product with Cost 100 and 21% IVA in a Category with 55% wholesale and 120% retail margins,
    sold in Packs of 10 (and by the box, a packaging of 10), the two Price Lists, and a Wholesale and a
    Retail Customer."""

    @classmethod
    def setup_pricing(cls):
        cls.iva21 = cls.env["account.tax"].create({"name": "IVA 21% (test)", "amount": 21, "type_tax_use": "sale"})
        cls.category = cls.env["product.category"].create(
            {"name": "Papelería", "wholesale_margin": 55, "retail_margin": 120}
        )
        cls.unit = cls.env.ref("uom.product_uom_unit")
        cls.box = cls.env["uom.uom"].create({"name": "Caja x10", "relative_uom_id": cls.unit.id, "relative_factor": 10})
        cls.ream = cls.env["product.product"].create(
            {
                "name": "Resma A4",
                "type": "consu",
                "is_storable": True,
                "categ_id": cls.category.id,
                "replacement_cost": 100,
                "pack_size": 10,
                "list_price": 1,
                "taxes_id": [(6, 0, cls.iva21.ids)],
                "uom_ids": [(4, cls.box.id)],
                "available_in_pos": True,
            }
        )
        cls.wholesale_list = cls._price_list("Mayorista", "wholesale")
        cls.retail_list = cls._price_list("Minorista", "retail")
        cls.wholesale_customer = cls.env["res.partner"].create(
            {
                "name": "Distribuidora Rivera",
                "property_product_pricelist": cls.wholesale_list.id,
                "customer_discount": 14,
            }
        )
        cls.retail_customer = cls.env["res.partner"].create(
            {"name": "Juana Pérez", "property_product_pricelist": cls.retail_list.id}
        )

    @classmethod
    def _price_list(cls, name, kind):
        return cls.env["product.pricelist"].create(
            {
                "name": name,
                "list_kind": kind,
                "item_ids": [(0, 0, {"applied_on": "3_global", "compute_price": "formula", "base": "category_margin"})],
            }
        )


class PricingCase(PricingFixtures, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_pricing()

    def price_with_iva(self, price_list, product, qty=1):
        price = price_list._get_product_price(product, qty)
        return self.iva21.compute_all(price, product=product)["total_included"]

    def bag_variants(self):
        """Two variants of one template, in the Category, with no Cost or Pack size yet."""
        size = self.env["product.attribute"].create(
            {"name": "Medida", "value_ids": [(0, 0, {"name": "20x30"}), (0, 0, {"name": "40x60"})]}
        )
        bag = self.env["product.template"].create(
            {
                "name": "Bolsa polipropileno",
                "categ_id": self.category.id,
                "attribute_line_ids": [(0, 0, {"attribute_id": size.id, "value_ids": [(6, 0, size.value_ids.ids)]})],
            }
        )
        return bag.product_variant_ids

    def receive(self, product, qty, price, discount=0.0, uom=None, user=None, taxes=None, bonus=0):
        """Confirm a purchase of `qty` at `price` (per `uom`), plus `bonus` units free on a second line
        (a bonificación), and validate its receipt, as `user` if given."""
        supplier = self.env["res.partner"].create({"name": "Papelera del Centro"})
        order = self.env["purchase.order"].create(
            {
                "partner_id": supplier.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "product_uom_id": (uom or product.uom_id).id,
                            "price_unit": price,
                            "discount": discount,
                            "tax_ids": [(6, 0, taxes.ids)] if taxes else [(5,)],
                        },
                    )
                ]
                + ([(0, 0, {"product_id": product.id, "product_qty": bonus, "price_unit": 0})] if bonus else []),
            }
        )
        order.button_confirm()
        picking = order.picking_ids.with_user(user) if user else order.picking_ids
        picking.button_validate()
        return order

    def sell(self, partner, qty, uom=None, product=None):
        """A quotation for `qty` of `product` (a ream by default) on the partner's own Price List; returns its line."""
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": (product or self.ream).id,
                            "product_uom_qty": qty,
                            "product_uom_id": (uom or self.unit).id,
                        },
                    )
                ],
            }
        )
        return order.order_line
