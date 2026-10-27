# shellcheck shell=bash
# The machine's one dev stack, shared by every worktree: Postgres, the filestore volume and the
# image (compose project pcp-dev in docker-compose.dev.yaml). Sourced from prototype/ by
# scripts/dev.sh, scripts/test.sh and dev-pull.sh.
dc() { docker compose -f docker-compose.dev.yaml "$@"; }
psql_q() { dc exec -T db psql -U odoo -d postgres -v ON_ERROR_STOP=1 -Atc "$1"; }

# Starting Postgres, building the image, and creating, copying or replacing a database happen
# under one machine-wide lock, so worktrees running at once never race on them.
stack_lock() {
  exec 9>"${XDG_RUNTIME_DIR:-/tmp}/pcp-dev-stack.lock"
  flock 9
}
stack_unlock() { flock -u 9; }

# The tag of the test image this worktree's files build (Dockerfile.test, on the dev image): one per
# set of inputs, so worktrees whose Dockerfile.test differs never retag each other's.
test_image_key() {
  local base
  base=$(docker image inspect -f '{{.Id}}' pcp-dev-odoo) || return 1
  (echo "$base"; cat Dockerfile.test requirements-test.txt) | sha256sum | cut -c1-12
}

# Postgres up and healthy, the filestore volume and the image present. Call holding stack_lock.
stack_up() {
  local out
  out=$(dc up -d --wait db 2>&1) || { echo "$out" >&2; return 1; }
  # The Odoo this stack served before each worktree had its own: it holds proto open, and a copy
  # of proto needs it unconnected.
  docker rm -f pcp-dev-odoo-1 >/dev/null 2>&1 || true
  # proto takes no connections (dev-pull.sh says why); this also closes one restored before that rule.
  psql_q "select 1 from pg_database where datname = 'proto' and datallowconn" | grep -q . \
    && psql_q 'alter database proto allow_connections false' >/dev/null
  # Created by hand for the per-worktree Odoos, which mount it as external; the labels make it
  # pcp-dev's own, so Compose takes it as created by the project.
  docker volume inspect pcp-dev_odoo-data >/dev/null 2>&1 \
    || docker volume create --label com.docker.compose.project=pcp-dev \
      --label com.docker.compose.volume=odoo-data pcp-dev_odoo-data >/dev/null
  if ! docker image inspect pcp-dev-odoo >/dev/null 2>&1; then
    echo "building the pcp-dev-odoo image (once, takes a few minutes)" >&2
    out=$(dc build odoo 2>&1) || { echo "$out" >&2; return 1; }
  fi
}
