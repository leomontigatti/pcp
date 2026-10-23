# Commands

`justfile` is the complete list of commands for this repo. Run them as `uv run just <recipe>`
(`uv run just` lists them). If a task needs a command that isn't a recipe, add the recipe
first instead of running an ad-hoc command, so the next run is the same.

## First time on a machine

`uv run just setup`, then `uv run just dev-pull` (needs SSH to `root@rylai` over Tailscale).

## Which instance

Recipes that talk to Odoo hit the **local** dev copy: this worktree's own Odoo and database, at
the URL `uv run just dev-up` prints (`admin`/`admin`). For `--target local`, `prototype/lib/env.py`
takes the URL and the database from that running instance, not from `prototype/.env` (one file,
linked into every worktree), and still refuses any host but localhost. The deployed instance needs `--target deployed`, and writes need `--yes-deployed` as well
(`prototype/lib/env.py`). Never pass `--yes-deployed` without the user asking for that run.

The local copy is neutralized: it cannot reach ARCA, so anything that asks for a CAE fails there
by design.

## As you go

`uv run just test <module>` each time a slice goes green: one addon's tests in a throwaway
database. Narrow it to one test with `TEST_TAGS='/<module>:<Class>.<test>' uv run just test <module>`
while you iterate. After a merge, `uv run just lint` and `uv run just test <module>` for the addons
it touched.

## Before committing

`uv run just gate`. It runs every linter, then the tests of every addon in `prototype/addons`, and
prints only failures plus a summary line. Lint may auto-fix files: rerun until it passes.

Tests run in throwaway databases cloned from a template that has the AR stack installed with demo
data. The first run after an image change builds the template (a few minutes), and runs started
meanwhile, from any worktree, wait for that one build; later runs take seconds. Full logs stay in `prototype/.dev/test-logs/` for a week.

## CI

`.github/workflows/ci.yml` runs the same recipes on every PR: `checks` (all pre-commit hooks, plus
gitleaks over the PR's commits) and `test`. `pr-title.yml` checks the title; check one before
opening a PR with `uv run just pr-title "<title>"`. Dependabot proposes action, uv, image-pip and
`odoo:19.0` digest bumps after a 7-day cooldown; addons pins move only through `bump-addons`.

## Day to day

| Need | Recipe |
| --- | --- |
| Start / stop this worktree's Odoo (prints its URL) | `dev-up` / `dev-down` |
| Copy `proto` into this worktree's database again | `dev-reset` |
| Fresh data from the deployed instance into `proto` | `dev-pull`, then `dev-reset` |
| Image, `repos.txt` or config changed | `dev-rebuild` |
| See why Odoo misbehaves | `dev-logs` |
| Run Python inside Odoo | `echo '<code>' \| uv run just dev-shell` |
| Every worktree's database, filestore and container; remove one | `dev-ls`; `dev-rm [key]` |
| Run tests | `test [module...]` |
| Configure the instance | `setup-proto` |
| Read the old system's database (a raw MySQL backup folder; never committed, never deployed) | `legacy-load <dir>`, then `echo '<sql>' \| uv run just legacy-sql`; `legacy-down` removes it |
| Move ADHOC/OCA addons forward | `bump-addons`, review the compare URLs, then `dev-rebuild` |
| Create or update the GitHub labels in `.github/labels.json` | `labels-sync` |

## Agent hooks

The project's Claude Code and Codex hooks ([agent-configuration.md](agent-configuration.md#project-hooks)) run the
same checks as you go: `ruff` formats each Python file an agent edits, and the Stop hook runs pre-commit on
the changed files before a turn can end. They never run the Odoo tests, and they do not replace
`uv run just gate`, which is still the check before a commit is done.

Agents only run the recipes listed in the `justfile`. A command that is not a recipe means a recipe to add
first, not an ad-hoc command.
