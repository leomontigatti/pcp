# Every command an agent or a person runs in this repo. `just` lists them; see
# docs/agents/validation.md for when to use which. Run through uv: `uv run just <recipe>`.

set shell := ["bash", "-euo", "pipefail", "-c"]

compose := "docker compose -f prototype/docker-compose.dev.yaml"

# One legacy database container per worktree, so two worktrees never query or remove each other's
legacy := "pcp-legacy-" + file_name(justfile_directory())

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

# Odoo tests in a throwaway db: all addons in prototype/addons, or the named modules.
# Narrow with TEST_TAGS='/mod:Class.test_x'. Prints failures only and one summary line.
test *modules:
    prototype/scripts/test.sh {{ modules }}

# Everything that must pass before a commit is done: lint, then tests. Failures only.
gate:
    #!/usr/bin/env bash
    set -uo pipefail
    fail=0
    if ! out=$(uv run pre-commit run --all-files 2>&1); then
      grep -vE '\.\.\.+(Passed|\(no files to check\)Skipped)$' <<<"$out"; fail=1
    fi
    [[ $fail == 0 ]] && echo "lint: PASS" || echo "lint: FAIL (files may have been auto-fixed; rerun)"
    prototype/scripts/test.sh || fail=1
    [[ $fail == 0 ]] && echo "gate: PASS" || { echo "gate: FAIL"; exit 1; }

# Check a PR title the way CI does (Conventional Commit; it becomes the squash commit subject)
pr-title title:
    PR_TITLE={{ quote(title) }} python3 .github/scripts/check_pr_title.py

# Replace the local dev copy with a neutralized snapshot of the deployed instance
dev-pull:
    prototype/dev-pull.sh

# Start the local dev stack and wait until Odoo answers
dev-up:
    {{ compose }} up -d --wait db
    {{ compose }} up -d odoo
    for _ in $(seq 150); do curl -sf http://localhost:8069/web/health >/dev/null && exit 0; sleep 2; done; echo "odoo not healthy: just dev-logs" >&2; exit 1

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

# Load a raw backup of the old system's MySQL 5.0 database (a folder of .frm/.MYD/.MYI) into a
# throwaway MySQL 5.5 container. Works on a copy under prototype/.dev/legacy; publishes no port.
legacy-load dir:
    #!/usr/bin/env bash
    set -euo pipefail
    src=$(realpath -e {{ quote(dir) }}); work=$(realpath -m prototype/.dev/legacy)
    [[ $src != "$work" && $src != "$work"/* ]] || { echo "the backup must live outside $work" >&2; exit 1; }
    {{ just_executable() }} legacy-down
    mkdir -p prototype/.dev/legacy/data/legacy
    cp "$src"/*.frm "$src"/*.MYD "$src"/*.MYI "$src"/db.opt prototype/.dev/legacy/data/legacy/
    docker run -d --name {{ legacy }} --user "$(id -u):$(id -g)" -e MYSQL_ALLOW_EMPTY_PASSWORD=1 \
      -v "$PWD/prototype/.dev/legacy/data:/var/lib/mysql" mysql:5.5.62 >/dev/null
    for _ in $(seq 60); do docker exec {{ legacy }} mysql -uroot -e 'select 1' legacy >/dev/null 2>&1 && exit 0; sleep 2; done
    docker logs --tail 30 {{ legacy }} >&2; exit 1

# Run SQL from stdin against the loaded legacy database; output is UTF-8, tab-separated
legacy-sql:
    docker exec -i {{ legacy }} mysql -uroot --default-character-set=utf8 legacy

# Remove the legacy container and its copy of the data (the data only once the container is gone)
legacy-down:
    docker version >/dev/null
    if docker container inspect {{ legacy }} >/dev/null 2>&1; then docker rm -f {{ legacy }} >/dev/null; fi
    rm -rf prototype/.dev/legacy

# Create or update the GitHub labels in .github/labels.json (idempotent; needs gh and jq)
labels-sync:
    jq -r '.groups[][] | [.name, .color, .description] | @tsv' .github/labels.json | while IFS=$'\t' read -r name color description; do gh label create "$name" --color "$color" --description "$description" --force; done

# Move addons pins in prototype/repos.txt to branch heads (all, or the named repos)
bump-addons *names:
    prototype/scripts/bump-addons.sh {{ names }}
