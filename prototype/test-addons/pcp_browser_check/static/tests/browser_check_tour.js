import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pcp_browser_check", {
    steps: () => [{ trigger: ".o_main_navbar" }],
});
