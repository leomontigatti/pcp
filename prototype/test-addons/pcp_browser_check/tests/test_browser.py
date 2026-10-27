from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestBrowser(HttpCase):
    def test_tour_runs(self):
        self.start_tour("/odoo", "pcp_browser_check", login="admin")
