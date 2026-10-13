# Commands

`justfile` is the complete list of commands for this repo. Run them as `uv run just <recipe>`
(`uv run just` lists them). If a task needs a command that isn't a recipe, add the recipe
first instead of running an ad-hoc command, so the next run is the same.

## First time on a machine

`uv run just setup`, then `uv run just dev-pull` (needs SSH to `rylai`).

## Which instance

Recipes that talk to Odoo hit the **local** dev copy (`http://localhost:8069`, `admin`/`admin`).
The deployed instance needs `--target deployed`, and writes need `--yes-deployed` as well
(`prototype/lib/env.py`). Never pass `--yes-deployed` without the user asking for that run.

The local copy is neutralized: it cannot reach ARCA, so anything that asks for a CAE fails there
by design.

## Day to day

| Need | Recipe |
| --- | --- |
| Start / stop the dev stack | `dev-up` / `dev-down` |
| Fresh data from the deployed instance | `dev-pull` |
| Image, `repos.txt` or config changed | `dev-rebuild` |
| See why Odoo misbehaves | `dev-logs` |
| Run Python inside Odoo | `echo '<code>' \| uv run just dev-shell` |
| Configure the instance | `setup-proto` |
| Move ADHOC/OCA addons forward | `bump-addons`, review the compare URLs, then `dev-rebuild` |
