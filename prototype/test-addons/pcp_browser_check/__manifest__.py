{
    "name": "PCP browser check",
    "summary": "Fails the test run when Odoo's browser tests cannot run",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "license": "LGPL-3",
    "author": "PCP",
    "depends": ["web_tour"],
    "assets": {
        "web.assets_tests": ["pcp_browser_check/static/tests/**/*"],
    },
}
