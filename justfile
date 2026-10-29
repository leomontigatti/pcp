# Every command an agent or a person runs in this repo. `just` lists them; see
# docs/agents/validation.md for when to use which. Run through uv: `uv run just <recipe>`.

set shell := ["bash", "-euo", "pipefail", "-c"]

# One legacy database container per worktree, so two worktrees never query or remove each other's
legacy := "pcp-legacy-" + replace_regex(sha256(justfile_directory()), '^(.{12}).*$', '$1')

# List recipes
default:
    @just --list --unsorted

# Install pinned tools and the pre-commit git hook; create prototype/.env if missing
setup:
    uv sync --locked
    install -m 0755 .githooks/pre-commit "$(git rev-parse --git-path hooks)/pre-commit"
    uv run pre-commit install-hooks
    [ -f prototype/.env ] || cp prototype/.env.example prototype/.env

# All linters and formatters on every file (fixes what it can; rerun to confirm)
lint:
    uv run pre-commit run --all-files --show-diff-on-failure

# Odoo tests in a throwaway db: all addons in prototype/addons, or the named modules.
# Narrow with TEST_TAGS='/mod:Class.test_x'. Prints failures only and one summary line.
test *modules:
    prototype/scripts/test.sh {{ modules }}

# Everything that must pass before a commit is done: lint, then the legacy and Odoo tests. Failures only.
gate:
    #!/usr/bin/env bash
    set -uo pipefail
    fail=0
    if ! out=$(uv run pre-commit run --all-files 2>&1); then
      grep -vE '\.\.\.+(Passed|\(no files to check\)Skipped)$' <<<"$out"; fail=1
    fi
    [[ $fail == 0 ]] && echo "lint: PASS" || echo "lint: FAIL (files may have been auto-fixed; rerun)"
    out=$(python3 -I -m unittest discover -s prototype/legacy -t prototype/legacy 2>&1) && echo "legacy-test: PASS" || { echo "$out"; fail=1; }
    prototype/scripts/test.sh || fail=1
    [[ $fail == 0 ]] && echo "gate: PASS" || { echo "gate: FAIL"; exit 1; }

# Check a PR title the way CI does (Conventional Commit; it becomes the squash commit subject)
pr-title title:
    PR_TITLE={{ quote(title) }} python3 .github/scripts/check_pr_title.py

# Replace proto, the golden copy worktrees copy from, with a neutralized snapshot of the deployed instance
dev-pull:
    prototype/dev-pull.sh

# Start this worktree's Odoo (its own database, copied from proto the first time) and print its URL
dev-up:
    prototype/scripts/dev.sh up

# Stop this worktree's Odoo (database and filestore kept)
dev-down:
    prototype/scripts/dev.sh down

# Re-copy this worktree's database and filestore from proto, dropping its own, then start it
dev-reset:
    prototype/scripts/dev.sh reset

# Every worktree's database, filestore and container, live or orphan (its worktree is gone)
dev-ls:
    prototype/scripts/dev.sh ls

# Remove a worktree's Odoo, database and filestore: this one's, or an orphan's by its dev-ls key
dev-rm key="":
    prototype/scripts/dev.sh rm {{ key }}

# Rebuild the shared image and restart this worktree's Odoo (after Dockerfile, repos.txt or config changes)
dev-rebuild:
    prototype/scripts/dev.sh rebuild

# Remove the test images left by earlier dev image or Dockerfile.test versions; run while no test runs
test-prune:
    prototype/scripts/dev.sh prune-tests

# Last N lines of this worktree's Odoo log
dev-logs n="200":
    prototype/scripts/dev.sh logs {{ n }}

# Odoo shell on this worktree's database; pipe Python on stdin for non-interactive use
dev-shell:
    prototype/scripts/dev.sh shell

# Configure the instance (this worktree's local copy by default; --target deployed --yes-deployed for Coolify)
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

# Propose the catalog review (#26) from the loaded legacy database: variant groups of the Warehouse
# catalog and Warehouse/Alberdi duplicates, as CSVs and a note for the client in <out>. Never touches Odoo.
catalog-review out:
    {{ just_executable() }} legacy-sql < prototype/legacy/catalog.sql | python3 -I prototype/legacy/catalog_review.py {{ quote(out) }}

# Unit tests of the legacy-data scripts in prototype/legacy (no database needed)
legacy-test:
    python3 -I -m unittest discover -s prototype/legacy -t prototype/legacy

# Remove the legacy container and its copy of the data (the data only once the container is gone)
legacy-down:
    #!/usr/bin/env bash
    set -euo pipefail
    # A failed listing aborts here; only a listing that succeeded and came back empty means "no container".
    ids=$(docker ps -aq --filter 'name=^/{{ legacy }}$')
    [[ -z $ids ]] || docker rm -f "$ids" >/dev/null
    left=$(docker ps -aq --filter 'name=^/{{ legacy }}$')
    [[ -z $left ]] || { echo "{{ legacy }} is still there; data kept" >&2; exit 1; }
    rm -rf prototype/.dev/legacy

# Create or update the GitHub labels in .github/labels.json (idempotent; needs gh and jq)
labels-sync:
    jq -r '.groups[][] | [.name, .color, .description] | @tsv' .github/labels.json | while IFS=$'\t' read -r name color description; do gh label create "$name" --color "$color" --description "$description" --force; done

# Move addons pins in prototype/repos.txt to branch heads (all, or the named repos)
bump-addons *names:
    prototype/scripts/bump-addons.sh {{ names }}
