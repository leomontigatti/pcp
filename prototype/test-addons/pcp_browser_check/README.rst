=================
PCP browser check
=================

Test-only: never deployed (it lives outside ``prototype/addons``) and never installed on an
instance. ``scripts/test.sh`` tests it on every full run: its one tour fails the run when the test
image's headless Chrome cannot start, so a run where Odoo's browser tests would be skipped does not
pass.
