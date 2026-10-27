{
    "name": "PCP Pricing",
    "summary": "Price Lists from replacement Cost and Category Margins; Customer and Pack Discounts",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "PCP",
    "license": "LGPL-3",
    "depends": ["sale", "purchase_stock", "point_of_sale"],
    "data": [
        "views/product_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": ["pcp_pricing/static/src/app/**/*"],
        "web.assets_tests": ["pcp_pricing/static/tests/tours/**/*"],
    },
}
