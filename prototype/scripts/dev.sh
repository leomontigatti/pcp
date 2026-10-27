#!/usr/bin/env bash
# This worktree's Odoo for checking screens: its own database, copied from proto with its
# filestore, served by its own container on the shared stack (lib/stack.sh). Every name derives
# from the worktree's path (the key), so no two worktrees share one, and nothing here writes proto.
#   scripts/dev.sh up         create the copy if missing, start Odoo, print its URL (idempotent)
#   scripts/dev.sh down       stop and remove this worktree's container (database and filestore kept)
#   scripts/dev.sh reset      re-copy this worktree's database and filestore from proto, then up
#   scripts/dev.sh rm [key]   remove a worktree's container, database and filestore (default: this one)
#   scripts/dev.sh ls         every worktree's resources, tab-separated, with live or orphan
#   scripts/dev.sh env        ODOO_URL and ODOO_DB of this worktree's running Odoo (for lib/env.*)
#   scripts/dev.sh shell      Odoo shell on this worktree's database; Python on stdin
#   scripts/dev.sh logs [n]   last n lines of this worktree's Odoo log
#   scripts/dev.sh rebuild    rebuild the shared image, then recreate this worktree's Odoo if it runs
#   scripts/dev.sh prune-tests  remove the test images but the one this worktree's files build
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source-path=SCRIPTDIR/.. source=lib/stack.sh
source lib/stack.sh

root=$(cd .. && pwd -P)
key=$(printf %s "$root" | sha256sum | cut -c1-12)
db="wt_$key"
port=

die() { echo "$*" >&2; exit 1; }
# Compose for one worktree's Odoo, this one's unless PCP_KEY says otherwise.
wc() {
  local k=${PCP_KEY:-$key}
  PCP_KEY=$k PCP_WORKTREE=${PCP_WORKTREE:-$root} PCP_PORT=${port:-0} \
    docker compose -p "pcp-wt-$k" -f docker-compose.worktree.yaml "$@"
}
container() { echo "pcp-wt-$1-odoo-1"; }
# Filestore operations, as root in the Postgres image (always present while the stack is up).
fs() { docker run --rm -v pcp-dev_odoo-data:/var/lib/odoo --entrypoint bash postgres:16 -c "$1"; }
# shellcheck disable=SC2016  # a Go template for docker inspect, not shell
ports_tmpl='{{range $p, $b := .HostConfig.PortBindings}}{{range $b}}{{.HostPort}}{{"\n"}}{{end}}{{end}}'
# A failed query stops the script: read as "no database", it would send up to create_copy, whose
# first step deletes the filestore. (Callers use it in a condition, where set -e does not reach.)
db_exists() {
  local r
  r=$(psql_q "select 1 from pg_database where datname = '$1'") || die "could not query Postgres"
  [[ -n $r ]]
}
host_port() {
  docker inspect -f "$ports_tmpl" "$(container "$1")" 2>/dev/null | grep . || true
}

# Copy proto into this worktree's database: the filestore first, so a copy cut short leaves no
# database and the next up starts over. Call holding stack_lock.
create_copy() {
  db_exists proto || die "no proto database to copy: uv run just dev-pull"
  echo "copying proto into $db" >&2
  fs "rm -rf /var/lib/odoo/filestore/$db && mkdir -p /var/lib/odoo/filestore \
    && if [ -d /var/lib/odoo/filestore/proto ]; then cp -a /var/lib/odoo/filestore/proto /var/lib/odoo/filestore/$db; fi"
  if ! psql_q "create database \"$db\" template proto" >/dev/null; then
    fs "rm -rf /var/lib/odoo/filestore/$db"
    die "could not copy proto (is something connected to it?)"
  fi
  psql_q "comment on database \"$db\" is '${root//\'/\'\'}'" >/dev/null
}

# Drop one worktree's database and filestore. The name is checked here, the last step before
# anything is deleted, so an empty or wrong key never reaches proto or another kind of database.
drop_copy() {
  local name=$1
  [[ $name =~ ^wt_[0-9a-f]{12}$ ]] || die "refusing to drop '$name': not a worktree database"
  psql_q "select pg_terminate_backend(pid) from pg_stat_activity where datname = '$name'" >/dev/null
  psql_q "drop database if exists \"$name\"" >/dev/null
  fs "rm -rf /var/lib/odoo/filestore/$name"
}

# The port this worktree's container already has, else the first free one from a start that
# derives from the key, so a worktree keeps its URL across restarts. Call holding stack_lock.
pick_port() {
  local p taken
  p=$(host_port "$key")
  [[ -n $p ]] && { echo "$p"; return; }
  taken=$( (docker ps -aq --filter label=pcp.worktree | xargs -r docker inspect -f "$ports_tmpl"
  ss -Hltn | awk '{sub(/.*:/, "", $4); print $4}') | sort -u)
  p=$((8100 + 16#${key:0:4} % 900))
  for _ in $(seq 900); do
    grep -qx "$p" <<<"$taken" || { echo "$p"; return; }
    p=$((p >= 8999 ? 8100 : p + 1))
  done
  die "no free port in 8100-8999"
}

wait_healthy() {
  for _ in $(seq 150); do
    curl -sf "http://localhost:$port/web/health" >/dev/null && return 0
    [[ $(docker inspect -f '{{.State.Running}}' "$(container "$key")" 2>/dev/null) == true ]] \
      || { wc logs --no-log-prefix --tail 40 odoo >&2; die "odoo exited: uv run just dev-logs"; }
    sleep 2
  done
  die "odoo not healthy after 5 minutes: uv run just dev-logs"
}

up() {
  stack_lock
  stack_up
  db_exists "$db" || create_copy
  port=$(pick_port)
  wc up -d "$@" odoo
  stack_unlock
  wait_healthy
  echo "http://localhost:$port (db $db, admin / admin)"
}

# The worktree a key belongs to: the path its database records, else its container's label.
# A failed query or listing fails it, rather than reading as "none recorded", which means orphan.
# Only a listing that succeeded and came back empty means "no container".
worktree_of() {
  local path
  path=$(psql_q "select coalesce(shobj_description(oid, 'pg_database'), '') from pg_database where datname = 'wt_$1'") || return 1
  if [[ -z $path ]]; then
    path=$(docker ps -a --filter "name=^/$(container "$1")$" --format '{{.Label "pcp.worktree"}}') || return 1
  fi
  echo "$path"
}
# live while the key's worktree exists; orphan once it is gone, or when none was recorded.
status_of() { [[ -n $1 && -d $1 ]] && echo live || echo orphan; }

# Every key that has a database, a filestore or a container, one tab-separated line each.
ls_all() {
  local dbs files k path ctr
  dbs=$(psql_q "select datname from pg_database where datname ~ '^wt_[0-9a-f]{12}$'")
  files=$(fs "ls /var/lib/odoo/filestore 2>/dev/null" | grep -E '^wt_[0-9a-f]{12}$' || true)
  printf 'key\tstatus\tdatabase\tfilestore\tcontainer\tworktree\n'
  for k in $( (echo "$dbs"; echo "$files"
    docker ps -a --filter label=pcp.worktree --format '{{.Label "com.docker.compose.project"}}' | sed 's/^pcp-wt-/wt_/') \
    | sed -n 's/^wt_//p' | sort -u); do
    path=$(worktree_of "$k")
    ctr=$(docker ps -a --filter "name=^/$(container "$k")$" --format '{{.State}}')
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$k" "$(status_of "$path")" \
      "$(grep -qx "wt_$k" <<<"$dbs" && echo "wt_$k" || echo -)" \
      "$(grep -qx "wt_$k" <<<"$files" && echo "wt_$k" || echo -)" "${ctr:--}" "${path:--}"
  done
}

# Remove one worktree's resources by key. Another worktree's are removed only once that worktree
# is gone, so a sweep cannot take a live worktree's database.
rm_key() {
  local k=${1#wt_} path=
  [[ $k =~ ^[0-9a-f]{12}$ ]] || die "not a worktree key: '$k' (see: uv run just dev-ls)"
  stack_lock
  stack_up
  if [[ $k != "$key" ]]; then
    path=$(worktree_of "$k")
    [[ $(status_of "$path") == orphan ]] || die "wt_$k belongs to $path, which still exists: run dev-rm there"
  fi
  PCP_KEY=$k PCP_WORKTREE=${path:-$root} wc down
  drop_copy "wt_$k"
  stack_unlock
  echo "removed wt_$k"
}

case "${1:-}" in
  up) up ;;
  down) wc down ;;
  reset)
    wc down
    stack_lock
    stack_up
    drop_copy "$db"
    stack_unlock
    up
    ;;
  rm) rm_key "${2:-$key}" ;;
  ls) stack_lock; stack_up; ls_all ;;
  env)
    port=$(host_port "$key")
    [[ -n $port && $(docker inspect -f '{{.State.Running}}' "$(container "$key")" 2>/dev/null) == true ]] \
      || die "this worktree's Odoo is not running: uv run just dev-up"
    echo "ODOO_URL=http://localhost:$port"
    echo "ODOO_DB=$db"
    ;;
  shell) wc exec -T odoo /entrypoint.sh odoo shell -d "$db" --no-http --log-level=warn ;;
  logs) wc logs --no-log-prefix --tail "${2:-200}" odoo ;;
  rebuild)
    stack_lock
    stack_up
    dc build odoo
    stack_unlock
    if [[ -n $(host_port "$key") ]]; then up --force-recreate; fi
    ;;
  prune-tests)
    # Each dev image rebuild or Dockerfile.test change leaves the previous test image (scripts/test.sh).
    # A worktree whose image goes builds it again on its next test run.
    stack_lock
    keep=$(test_image_key)
    for tag in $(docker image ls --format '{{.Tag}}' pcp-dev-odoo-test); do
      # One a running test uses is refused (docker says so), and the rest still go.
      [[ $tag == "$keep" ]] || docker image rm "pcp-dev-odoo-test:$tag" || true
    done
    stack_unlock
    ;;
  *) die "usage: scripts/dev.sh up|down|reset|rm [key]|ls|env|shell|logs [n]|rebuild|prune-tests" ;;
esac
