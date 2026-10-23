#!/usr/bin/env bash
# Replace proto, the golden copy on the shared dev stack (docker-compose.dev.yaml), with a snapshot
# of the deployed prototype: database and filestore. Read-only on the server. Worktrees serve
# copies of proto (scripts/dev.sh), never proto itself, and proto takes no connections once
# restored; `just dev-reset` re-copies a worktree's database from it.
# entrypoint.sh upgrades and neutralizes proto here (crons and mail servers off, every ARCA web
# service URL pointed nowhere), and every copy again on each start, so none can spend invoice
# numbers on the real fiscal points; dev-pull fails if the upgrade or the neutralization does.
set -euo pipefail
cd "$(dirname "$0")"
SSH_HOST="${SSH_HOST:-root@rylai}"
APP_UUID="${APP_UUID:-qcx1w6nrzvfsagjemdd4t6aa}"
DB="${DB:-proto}"
# shellcheck source-path=SCRIPTDIR source=lib/stack.sh
source lib/stack.sh
[[ -f .env ]] || cp .env.example .env

remote_db=$(ssh "$SSH_HOST" "docker ps -qf name=^db-$APP_UUID")
remote_odoo=$(ssh "$SSH_HOST" "docker ps -qf name=^odoo-$APP_UUID")

echo ">>> snapshot from $SSH_HOST"
mkdir -p .dev
ssh "$SSH_HOST" "docker exec $remote_db pg_dump -U odoo -Fc $DB" > ".dev/$DB.dump"
ssh "$SSH_HOST" "docker exec $remote_odoo tar -C /var/lib/odoo/filestore -cf - $DB" > .dev/filestore.tar

echo ">>> restore"
# Held until the script exits, after the trap below has closed proto, so no worktree copies it
# while it is half restored.
stack_lock
stack_up
dc exec -T db dropdb -U odoo --if-exists --force "$DB"
dc exec -T db createdb -U odoo "$DB"
# Closed to connections on any exit from here, a failed upgrade or neutralization included: every
# worktree's Odoo shares this Postgres, and Odoo's RPC takes any database name, past --db-filter.
# Copies still work: copying a template does not connect to it.
trap 'dc exec -T db psql -U odoo -d postgres -qc "alter database \"$DB\" allow_connections false"' EXIT
dc exec -T db pg_restore -U odoo --no-owner -d "$DB" < ".dev/$DB.dump"
dc run --rm --no-deps --user root -v "$PWD/.dev:/snap:ro" --entrypoint bash odoo -c \
  "rm -rf /var/lib/odoo/filestore/$DB && mkdir -p /var/lib/odoo/filestore \
   && tar -C /var/lib/odoo/filestore -xf /snap/filestore.tar && chown -R odoo:odoo /var/lib/odoo"

echo ">>> upgrade and neutralize (entrypoint.sh)"
echo "env['res.users'].browse(2).password = 'admin'; env.cr.commit()" | dc run --rm -T -e AUTO_UPDATE_DB= odoo odoo shell -d "$DB" --no-http --log-level=warn
dc run --rm --no-deps -T -e AUTO_UPDATE_DB="$DB" odoo true
echo ">>> $DB replaced (login admin / admin; other users keep their deployed passwords)."
echo "    Worktrees keep their copies: uv run just dev-reset re-copies one, uv run just dev-up creates a missing one."
