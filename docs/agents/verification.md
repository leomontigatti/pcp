# Verification

How to prove a change to what a user sees: a view, a report, a printed document, a wizard, the
point of sale. Every check here runs against the **local** copy, never the deployed instance: the
deployed one carries the real CUIT, the ARCA certificate and CAE-backed invoices
([validation.md](validation.md#which-instance)).

## Launch

`uv run just dev-up` starts **this worktree's** Odoo and prints its URL, `http://localhost:<port>`
(sign in as `admin`/`admin`). It serves this worktree's `prototype/addons` and its own database,
`wt_<key>`, a copy of `proto` with its filestore made the first time; the key and the port derive
from the worktree's path, so two worktrees never share either, and the port usually stays the same
across restarts (when two keys start from the same port, the second gets the next free one). Run it from the worktree whose code you are checking, never from another one; it is
idempotent and quick (seconds once the copy exists), so rerun it to read the URL again.

What one machine shares, every worktree's Odoo runs on: one Postgres (with `proto`, the test
templates and every worktree's copy), one filestore volume and one image. `dev-up` starts
Postgres when it is down; nothing per worktree stops it.

Data, in this order of preference:

- `uv run just scenarios`: the acceptance flows of § Feature map, run against this worktree's
  database. They create real documents and are safe to rerun.
- `uv run just setup-proto`: the instance's configuration (company, warehouses, Fiscal Points, price
  lists, products), idempotent.
- `uv run just dev-reset`: drop this worktree's copy and copy `proto` again, for a clean start.
- `uv run just dev-pull`: a neutralized snapshot of the deployed instance, replacing `proto`. The
  only data that comes from the deployed instance, and only through this recipe. It leaves every
  worktree's copy as it was: `dev-reset` takes the new data into one.

`proto` is the golden copy, and nothing in a worktree writes to it: `dev-pull` closes it to
connections once restored, because Odoo's RPC takes any database name past `--db-filter`, and
every worktree's Odoo shares its Postgres.

After a change to the Dockerfile, `prototype/repos.txt` or the Odoo config, `uv run just
dev-rebuild`: it rebuilds the shared image from this worktree's files and recreates this worktree's
Odoo. Other worktrees keep the old image until their next `dev-up` or `dev-rebuild`.

## Doctor

- `uv run just dev-up` again: it is idempotent, and it fails with a pointer to the logs when Odoo
  exits (a failed upgrade stops it) or does not become healthy within five minutes.
- `uv run just dev-logs` (or `dev-logs 1000`) for this worktree's Odoo log: diagnose from it, not
  from guesses.
- `echo '<code>' | uv run just dev-shell` to read a record's state from inside this worktree's
  database.
- `uv run just dev-ls` lists every worktree's database, filestore and container, so you can tell
  whose instance a port or a database is.
- Signed out every time you switch tabs: browsers keep cookies per host, not per port, so two
  worktrees' instances on `localhost` share one session cookie. Use one at a time in a browser, or
  a private window for the second.
- The local copy cannot reach ARCA by design: anything that asks for a CAE fails there. That
  failure is not a broken setup.

## Drive

Drive the flow through the path a user takes, then read the result back: the document text, the
record's state, the printed output.

- **In a T3 thread**: the preview tools, as the shared `PREVIEW.md` of the `implement` skill says,
  on the URL `dev-up` printed, signing in as `admin`/`admin`. They have not been tried against
  Odoo's login yet (`preview-odoo-login` in [t3-dependencies.md](t3-dependencies.md)): note in
  the final report where they fell short, and fall back to the next bullet.
- **Outside T3, or as the fallback**: a scenario from `uv run just scenarios` when one covers the
  flow, or a snippet through `echo '<code>' | uv run just dev-shell` when the flow is a model
  method. A route can be driven with an `HttpCase` test ([tdd-odoo.md](tdd-odoo.md)).

Never ask the user to check a screen by hand: drive it and show the result. When a screen could
not be driven, the final report names it, so the reviewer knows which part rests on the tests
alone.

## Evidence

Evidence is for the user, in the thread: they approve it there before the PR opens, and the PR
carries none of it, neither images nor a before-and-after section.

- The **before** is captured before the first edit, the **after** on the same screen, data and
  account.
- A screen: a `preview_snapshot` with `save: true` in T3, shown in the thread as an image embedded
  by its absolute path. Until the preview tools work against Odoo (`preview-odoo-login` in
  [t3-dependencies.md](t3-dependencies.md)), the text below is the evidence.
- Motion or an interaction: a recording (`preview_recording_start` and `preview_recording_stop`),
  linked in the thread by its absolute path.
- A printed document or a record: its text before and after, from `dev-shell` or the scenario's
  output, quoted in the thread.
- A test that failed without the change is evidence too; a list of green commands is not.
- Take evidence from the local copy only, and keep it out of the repo.

## Cleanup

Close the preview tab with `t3_preview_close`, then stop this worktree's Odoo with
`uv run just dev-down`: it runs only while this worktree checks a screen, and its database and
filestore are kept for the next `dev-up`. Leave Postgres running, since other worktrees and the
tests use it. Never stop anything with `pkill`, and never stop or remove another worktree's
instance: `uv run just dev-rm` removes this worktree's database and filestore when they are no longer
wanted, and the orphans of deleted worktrees go with the `housekeeping` skill
([housekeeping.md](housekeeping.md)).

## Feature map

Which flow proves which area. The numbers are the sections `uv run just scenarios` prints.

| Area                                                        | Flow                                                                                  |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Wholesale prices, Customer and Pack discounts, Factura A     | Scenario 1: a Wholesale Customer buys closed Packs at the Warehouse; invoice and delivery |
| Cross-Location Sale, reservations at the source             | Scenario 2: a Retail Store sells a Product held at the Warehouse                       |
| Supplier bills, Perceptions (IIBB Córdoba)                  | Scenario 3: a supplier bill with an IIBB perception                                    |
| Stock Transfers, Replenishment Requests, stock in transit   | Scenario 4: a resupply route from the Warehouse to a Retail Store, dispatched and in transit |
| Internal Consumption                                        | Scenario 5: a Retail Store consumes stock to its consumption location                  |
| Point of Sale screens                                       | No scenario yet: drive the POS in the browser, or say it was not seen; a POS tour in the addon's tests runs in `uv run just test` ([tdd-odoo.md](tdd-odoo.md)) |
| Printed documents (invoices, reports)                       | Print from the record in the browser; the text through `dev-shell` as the fallback     |
| Anything that asks ARCA for a CAE                           | Cannot be driven locally: the test with the ARCA client mocked ([tdd-odoo.md](tdd-odoo.md)) |
