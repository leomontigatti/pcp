#!/usr/bin/env bash
# Run Odoo tests in a throwaway database on the dev stack's Postgres.
#   scripts/test.sh               every addon in addons/, plus test-addons/pcp_browser_check
#   scripts/test.sh mod...        these addons (anything on the addons path)
#   TEST_TAGS=/mod:Class.test_x scripts/test.sh mod    narrower selection
# The AR stack (BASE_MODULES, with demo data) is installed once per image into a template
# database; each run clones it, installs or updates the target modules with tests on, and
# drops the clone. Prints only failures, then one summary line. Exit 0 iff everything passed.
# Tests run in the test image (Dockerfile.test): the dev image plus the browser HttpCase tours need.
# pcp_browser_check runs one tour on every full run, so a run where tours cannot run fails.
set -euo pipefail
cd "$(dirname "$0")/.."
BASE_MODULES=l10n_ar_fiscal_ws,l10n_ar_tax,point_of_sale,sale_management,stock,purchase
# shellcheck source-path=SCRIPTDIR/.. source=lib/stack.sh
source lib/stack.sh
odoo_run() { dc run --rm --no-deps -T -e AUTO_UPDATE_DB= odoo-test odoo "$@"; }

# Build the test image this worktree's files name (test_image_key) if missing. Call holding stack_lock.
test_image_up() {
  local out
  PCP_TEST_KEY=$(test_image_key)
  export PCP_TEST_KEY
  docker image inspect "pcp-dev-odoo-test:$PCP_TEST_KEY" >/dev/null 2>&1 && return
  echo "building the pcp-dev-odoo-test image (after a change to the dev image or Dockerfile.test, takes a minute)" >&2
  out=$(tar -c Dockerfile.test requirements-test.txt \
    | docker build -q -f Dockerfile.test -t "pcp-dev-odoo-test:$PCP_TEST_KEY" - 2>&1) \
    || { echo "$out" >&2; return 1; }
}

mods=("$@")
if [[ ${#mods[@]} == 0 ]]; then
  mapfile -t mods < <(find addons -mindepth 2 -maxdepth 2 -name __manifest__.py -printf '%h\n' | xargs -rn1 basename | sort)
  mods+=(pcp_browser_check)
fi
csv=$(IFS=,; echo "${mods[*]}")
tags="${TEST_TAGS:-$(printf '/%s,' "${mods[@]}" | sed 's/,$//')}"

mkdir -p .dev/test-logs
find .dev/test-logs -type f -mtime +7 -delete
log=".dev/test-logs/$(date +%Y%m%d-%H%M%S).log"
stack_lock
stack_up
test_image_up
stack_unlock

image=$(docker image inspect -f '{{.Id}}' "pcp-dev-odoo-test:$PCP_TEST_KEY")
template="tmpl_$(echo "$image $BASE_MODULES" | sha256sum | cut -c1-12)"
# Runs hold the template lock shared until they have cloned it. One run builds a missing template
# under the exclusive lock, and keeps it through its own clone: runs that start meanwhile wait for
# it, then find it built, and the old templates it drops are no longer being cloned.
# A failed query stops the run: read as "missing", it would send a run holding only the shared lock
# into the build, which drops the templates other runs are cloning.
template_exists() {
  local r
  r=$(psql_q "select 1 from pg_database where datname = '$template'") || { echo "test: FAIL querying Postgres" >&2; exit 1; }
  [[ -n $r ]]
}
exec 8>"${XDG_RUNTIME_DIR:-/tmp}/pcp-dev-template.lock"
flock -s 8
if ! template_exists; then
  flock 8
fi
if ! template_exists; then
  echo "test: building template $template (once per image, takes a few minutes)" >&2
  for old in $(psql_q "select datname from pg_database where datname like 'tmpl\_%'"); do
    psql_q "drop database \"$old\"" >/dev/null
  done
  if ! odoo_run -d "$template" -i "$BASE_MODULES" --with-demo --stop-after-init --no-http --log-level=warn >"$log.template" 2>&1; then
    psql_q "drop database if exists \"$template\"" >/dev/null
    echo "test: FAIL building template, see prototype/$log.template" >&2; exit 1
  fi
fi

db="test_$$"
cleanup() {
  psql_q "drop database if exists \"$db\"" >/dev/null 2>&1 || true
  dc run --rm --no-deps -T --entrypoint rm odoo -rf "/var/lib/odoo/filestore/$db" >/dev/null 2>&1 || true
}
trap cleanup EXIT
psql_q "select pg_terminate_backend(pid) from pg_stat_activity where datname = '$template'" >/dev/null
psql_q "create database \"$db\" template \"$template\"" >/dev/null
dc run --rm --no-deps -T --entrypoint cp odoo -a "/var/lib/odoo/filestore/$template" "/var/lib/odoo/filestore/$db" >/dev/null 2>&1 || true
flock -u 8

installed=$(dc exec -T db psql -U odoo -d "$db" -Atc \
  "select name from ir_module_module where state = 'installed' and name = any(string_to_array('$csv', ','))" | paste -sd,)
install=$(comm -23 <(tr , '\n' <<<"$csv" | sort) <(tr , '\n' <<<"$installed" | sort) | paste -sd,)
args=(-d "$db" --test-tags "$tags" --stop-after-init)
[[ -n "$install" ]] && args+=(-i "$install")
[[ -n "$installed" ]] && args+=(-u "$installed")

set +e
odoo_run "${args[@]}" >"$log" 2>&1
rc=$?
# Warnings fail too, as in OCA's CI. Ignored: addons/ has no module yet (goes away with the first one).
uv run --locked checklog-odoo --no-echo --ignore "invalid addons directory '/opt/odoo-addons/pcp'" "$log" >"$log.check" 2>&1
check=$?
# A browser test that could not start its browser is skipped, some ways with no warning for checklog.
skips=$(grep -E ' skipped .* : .*([Cc]hrome|websocket)' "$log" || true)
set -e

result=$( (grep -oE '[0-9]+ failed, [0-9]+ error\(s\) of [0-9]+ tests' "$log" || true) | awk '{f+=$1; e+=$3; n+=$6} END {if (NR) printf "%d tests, %d failed, %d errors", n, f, e; else printf "no test summary"}')
if [[ $rc == 0 && $check == 0 && -z $skips ]]; then
  echo "test: PASS $csv ($result)"
else
  grep -E ' (ERROR|CRITICAL) |^(FAIL|ERROR):|^Traceback|^\S*Error: ' "$log" | head -60 || true
  sed -n '/caused failure/,/^$/p' "$log.check" | grep -vE ' (ERROR|CRITICAL) |caused failure|^$' | head -20 || true
  [[ -z $skips ]] || echo "$skips"
  echo "test: FAIL $csv ($result; odoo exit $rc, checklog exit $check) log: prototype/$log"
  exit 1
fi
