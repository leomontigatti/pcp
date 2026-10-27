import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";

function pay() {
    return [
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.clickNextOrder(),
    ].flat();
}

function sell(customer, quantity) {
    return [
        ProductScreen.clickPartnerButton(),
        ProductScreen.clickCustomer(customer),
        ProductScreen.addOrderline("Resma A4", quantity),
        pay(),
    ].flat();
}

// A cashier scanning or tapping the product once per unit: the units merge into one line,
// which reaches the Pack Discount at the tenth.
function sellUnitByUnit(customer, units) {
    return [
        ProductScreen.clickPartnerButton(),
        ProductScreen.clickCustomer(customer),
        ...Array.from({ length: units }, () => ProductScreen.clickDisplayedProduct("Resma A4")),
        ProductScreen.selectedOrderlineHas("Resma A4", String(units)),
        pay(),
    ].flat();
}

registry.category("web_tour.tours").add("pcp_pricing_pos_discounts", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            sellUnitByUnit("Distribuidora Rivera", 10),
            sell("Distribuidora Rivera", "1"),
            sell("Juana Pérez", "10"),
        ].flat(),
});
