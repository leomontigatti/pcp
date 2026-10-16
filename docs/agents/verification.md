# Verification

How to prove a change to what a user sees: a view, a report, a printed document, a wizard, the
point of sale. Every check here runs against the **local** copy, never the deployed instance: the
deployed one carries the real CUIT, the ARCA certificate and CAE-backed invoices
([validation.md](validation.md#which-instance)).

## Launch

`uv run just dev-up` starts the local stack and waits until Odoo answers on
`http://localhost:8069` (sign in as `admin`/`admin`, database `proto`). It is one stack for the
machine, and every worktree sees the same database: start it from any worktree, and never start a
second one (an `implement-spec` implementer uses the orchestrator's).

Data, in this order of preference:

- `uv run just scenarios`: the acceptance flows of § Feature map, run against the local database.
  They create real documents and are safe to rerun.
- `uv run just setup-proto`: the instance's configuration (company, warehouses, Fiscal Points, price
  lists, products), idempotent.
- `uv run just dev-pull`: a neutralized snapshot of the deployed instance, replacing the local
  database. The only data that comes from the deployed instance, and only through this recipe.

After a change to the Dockerfile, `prototype/repos.txt` or the Odoo config, `uv run just dev-rebuild`.

## Doctor

- `uv run just dev-up` again: it is idempotent, and it fails with a pointer to the logs when Odoo
  does not become healthy within five minutes.
- `uv run just dev-logs` (or `dev-logs 1000`) for Odoo's log: diagnose from it, not from guesses.
- `echo '<code>' | uv run just dev-shell` to read a record's state from inside Odoo.
- The local copy cannot reach ARCA by design: anything that asks for a CAE fails there. That
  failure is not a broken setup.

## Drive

Drive the flow through the path a user takes, then read the result back: the document text, the
record's state, the printed output.

- **In a T3 thread**: the preview tools, as the shared `PREVIEW.md` of the `implement` skill says,
  on `http://localhost:8069`, signing in as `admin`/`admin`. They have not been tried against
  Odoo's login yet (`preview-odoo-login` in [t3-dependencies.md](t3-dependencies.md)): note in
  the final report where they fell short, and fall back to the next bullet.
- **Outside T3, or as the fallback**: a scenario from `uv run just scenarios` when one covers the
  flow, or a snippet through `echo '<code>' | uv run just dev-shell` when the flow is a model
  method. A route can be driven with an `HttpCase` test ([tdd-odoo.md](tdd-odoo.md)).

Never ask the user to check a screen by hand: drive it and show the result. When a screen could
not be driven, the final report names it, so the reviewer knows which part rests on the tests
alone.

## Evidence

- The **before** is captured before the first edit, the **after** on the same screen, data and
  account.
- A screen: a `preview_snapshot` with `save: true` in T3. Pcp has no image upload yet, so a
  screenshot is attached to the PR by hand, and the PR says so; until then the text below is the
  evidence.
- A printed document or a record: its text before and after, from `dev-shell` or the scenario's
  output, pasted into the PR's Evidence.
- A test that failed without the change is evidence too; a list of green commands is not.
- Never take evidence from the deployed instance, and never commit PR-only evidence to the repo.

## Cleanup

Close the preview tab with `t3_preview_close`. The stack is shared with every other worktree, so
leave it running unless this run started it and no other thread is using it; then stop it with
`uv run just dev-down` (the data is kept). Never stop it with `pkill`.

## Feature map

Which flow proves which area. The numbers are the sections `uv run just scenarios` prints.

| Area                                                        | Flow                                                                                  |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Wholesale prices, Customer and Pack discounts, Factura A     | Scenario 1: a Wholesale Customer buys closed Packs at the Warehouse; invoice and delivery |
| Cross-Location Sale, reservations at the source             | Scenario 2: a Retail Store sells a Product held at the Warehouse                       |
| Supplier bills, Perceptions (IIBB Córdoba)                  | Scenario 3: a supplier bill with an IIBB perception                                    |
| Stock Transfers, Replenishment Requests, stock in transit   | Scenario 4: a resupply route from the Warehouse to a Retail Store, dispatched and in transit |
| Internal Consumption                                        | Scenario 5: a Retail Store consumes stock to its consumption location                  |
| Point of Sale screens                                       | No scenario yet: drive the POS in the browser, or say it was not seen                  |
| Printed documents (invoices, reports)                       | Print from the record in the browser; the text through `dev-shell` as the fallback     |
| Anything that asks ARCA for a CAE                           | Cannot be driven locally: the test with the ARCA client mocked ([tdd-odoo.md](tdd-odoo.md)) |
