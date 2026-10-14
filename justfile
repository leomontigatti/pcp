# Every command an agent or a person runs in this repo. `just` lists them; see
# docs/agents/validation.md for when to use which. Run through uv: `uv run just <recipe>`.

set shell := ["bash", "-euo", "pipefail", "-c"]

compose := "docker compose -f prototype/docker-compose.dev.yaml"

# List recipes
default:
    @just --list --unsorted

# Install pinned tools and the pre-commit git hook; create prototype/.env if missing
setup:
    uv sync --locked
    uv run pre-commit install --install-hooks
    [ -f prototype/.env ] || cp prototype/.env.example prototype/.env

# All linters and formatters on every file (fixes what it can; rerun to confirm)
lint:
    uv run pre-commit run --all-files --show-diff-on-failure

# Replace the local dev copy with a neutralized snapshot of the deployed instance
dev-pull:
    prototype/dev-pull.sh

# Start the local dev stack and wait until Odoo answers
dev-up:
    {{ compose }} up -d --wait db
    {{ compose }} up -d odoo
    for _ in $(seq 60); do curl -sf http://localhost:8069/web/health >/dev/null && exit 0; sleep 2; done; echo "odoo not healthy: just dev-logs" >&2; exit 1

# Stop the local dev stack (data kept)
dev-down:
    {{ compose }} down

# Rebuild the image and restart Odoo (after Dockerfile, repos.txt or config changes)
dev-rebuild:
    {{ compose }} build odoo
    {{ compose }} up -d --force-recreate odoo

# Last N lines of Odoo's log
dev-logs n="200":
    {{ compose }} logs --no-log-prefix --tail {{ n }} odoo

# Odoo shell on the local db; pipe Python on stdin for non-interactive use
dev-shell db="proto":
    {{ compose }} exec -T odoo /entrypoint.sh odoo shell -d {{ db }} --no-http --log-level=warn

# Configure the instance (local by default; --target deployed --yes-deployed for Coolify)
setup-proto *args:
    cd prototype && uv run python setup-proto.py {{ args }}

# Run the acceptance scenarios (same targeting as setup-proto)
scenarios *args:
    cd prototype && uv run python scenarios.py {{ args }}

# Move addons pins in prototype/repos.txt to branch heads (all, or the named repos)
bump-addons *names:
    prototype/scripts/bump-addons.sh {{ names }}
