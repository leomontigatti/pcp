import { patch } from "@web/core/utils/patch";
import { roundPrecision } from "@web/core/utils/numbers";
import { ProductTemplateAccounting } from "@point_of_sale/app/models/accounting/product_template_accounting";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/services/pos_store";

// The rule getPrice applies, found in the same order it searches them.
function findRule(productTmpl, pricelist, quantity, variant) {
    const candidates = [
        () => (variant ? pricelist.getRulesByProductId(variant.id) : []),
        () => pricelist.getRulesByTmplId(productTmpl.id),
        () =>
            productTmpl.models["product.pricelist.item"].readMany(
                pricelist.getCategoryRulesIds(productTmpl.parentCategories)
            ),
        () => productTmpl.models["product.pricelist.item"].readMany(pricelist.getGlobalRulesIds()),
    ];
    for (const rules of candidates) {
        const rule = pricelist.findBestRule(rules(), quantity);
        if (rule) {
            return rule;
        }
    }
    return null;
}

// Mirrors product.product.is_whole_packs.
function isWholePacks(product, qty) {
    if (!(product.pack_size > 0) || qty <= 0) {
        return false;
    }
    const packs = qty / product.pack_size;
    return Math.abs(packs - Math.round(packs)) < 5e-7; // float_is_zero at 6 digits
}

// Mirrors product.pricelist.item._compute_base_price for the "category_margin" base, which
// Odoo's getPrice does not know and would price at the Sales Price.
patch(ProductTemplateAccounting.prototype, {
    getPrice(pricelist, quantity, price_extra = 0, recurring = false, variant = false, ...rest) {
        const price = super.getPrice(pricelist, quantity, price_extra, recurring, variant, ...rest);
        const productTmpl = variant?.product_tmpl_id || this;
        const category = productTmpl.categ_id;
        const rule = pricelist && category && findRule(productTmpl, pricelist, quantity, variant);
        if (rule?.base !== "category_margin" || rule.compute_price !== "formula") {
            return price;
        }
        const margin =
            pricelist.list_kind === "wholesale" ? category.wholesale_margin : category.retail_margin;
        const cost = variant ? variant.replacement_cost : productTmpl.replacement_cost;
        const base = cost * (1 + margin / 100);
        let result = base - base * ((rule.price_discount || 0) / 100);
        if (rule.price_round) {
            result = roundPrecision(result, rule.price_round);
        }
        result += rule.price_surcharge || 0;
        if (rule.price_min_margin) {
            result = Math.max(result, base + rule.price_min_margin);
        }
        if (rule.price_max_margin) {
            result = Math.min(result, base + rule.price_max_margin);
        }
        return result;
    },
});

// Mirrors product.pricelist.line_discount: the Customer Discount, plus the Pack Discount on a
// whole, nonzero number of the variant's Packs, only on the Wholesale List.
patch(PosOrderline.prototype, {
    setQuantity(quantity, keep_price) {
        const result = super.setQuantity(...arguments);
        this.applyListDiscount();
        return result;
    },
    // Odoo merges only lines with equal discounts; two lines that each carry their own list
    // discount (14% loose, 19% once a Pack) are the same sale and merge, the merged quantity then
    // setting the discount again.
    canBeMergedWith(orderline) {
        if (!(this.carriesListDiscount() && orderline.carriesListDiscount())) {
            return super.canBeMergedWith(orderline);
        }
        const own = this.discount;
        this.discount = orderline.discount;
        try {
            return super.canBeMergedWith(orderline);
        } finally {
            this.discount = own;
        }
    },
    listDiscount() {
        const order = this.order_id;
        const pricelist = order?.pricelist_id;
        if (!pricelist?.list_kind || this.refunded_orderline_id || this.combo_parent_id) {
            return null;
        }
        if (pricelist.list_kind !== "wholesale") {
            return 0;
        }
        let discount = order.partner_id?.customer_discount || 0;
        if (isWholePacks(this.product_id, this.getQuantity())) {
            discount += order.company_id.pack_discount;
        }
        return discount;
    },
    carriesListDiscount() {
        const discount = this.listDiscount();
        return discount !== null && this.getDiscount() === discount;
    },
    applyListDiscount() {
        const discount = this.listDiscount();
        if (discount !== null) {
            this.setDiscount(discount);
        }
    },
});

patch(PosOrder.prototype, {
    setPricelist(pricelist) {
        const result = super.setPricelist(...arguments);
        for (const line of this.lines) {
            line.applyListDiscount();
        }
        return result;
    },
});

// A new line gets its list discount before Odoo tries to merge it into an existing one.
patch(PosStore.prototype, {
    tryMergeOrderline(order, line) {
        line.applyListDiscount();
        return super.tryMergeOrderline(...arguments);
    },
});
