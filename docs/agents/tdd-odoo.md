# Test-first in Odoo

The `tdd` skill's notes for this stack: code that touches models, the ORM, the database, a
controller route or a report in an addon under `prototype/addons/`.

## Seams

The seam is usually a model method called through the ORM on a recordset the test creates, or a
controller route. Assert on what a caller sees: the record's state after a confirm, the amounts,
the number assigned, the printed text. Never on how a method builds its query.

## Test cases

- `TransactionCase` for model logic, `HttpCase` for a route or the web client. Both roll the
  database back, so use the test database instead of mocking the ORM.
- A test lives in the addon's `tests/` package, and Odoo collects only the modules
  `tests/__init__.py` imports: import every new test module there.
- Fixtures: extend the addon's `tests/common.py`, or the `setUpClass` of the nearest test class,
  before adding a support file.
- Run one addon with `uv run just test <module>`, one test with
  `TEST_TAGS='/<module>:<Class>.<test>' uv run just test <module>` ([validation.md](validation.md#as-you-go)).

## What not to test

What the framework proves: a field type, a `required`, an access rule Odoo enforces as declared.
Test what it cannot: rounding and sums of amounts, ordering of postings, state after a confirm,
numbering, the business logic's edge cases.

Text earns an assertion when code computes it, when the law fixes it (`"Nota de Crédito C"`), or
when a real bug produced the wrong text.

## Mocking

Mock only the boundary: ARCA's webservices (the client in `l10n_ar_fiscal_ws`), email, a payment
gateway, the clock. Never your own models or the ORM. Patch one specific method
(`unittest.mock.patch.object(<client class>, "<method>", return_value=...)`) and assert on what the
model does with the answer, not on the answer itself. The local copy cannot reach ARCA, so a flow
that asks for a CAE is proven this way.

## Migrations

A module's version is the one in its `__manifest__.py`, and a migration script hangs on it under
`<module>/migrations/<version>/`. Add one, or bump the version, only when the change alters the
schema or the data. Two tickets that touch the same module's manifest or migrations collide, so
`implement-spec` serialises them; a ticket that does not say whether it touches a module's schema
counts as one that does.
