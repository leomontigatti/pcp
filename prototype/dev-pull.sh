#!/usr/bin/env bash
# Replace the local dev copy (docker-compose.dev.yaml) with a snapshot of the deployed prototype:
# database and filestore. Read-only on the server.
# The dev service's entrypoint neutralizes the copy on every start (crons and mail servers off,
# every ARCA web service URL pointed nowhere), so it cannot spend invoice numbers on the real
# fiscal points; dev-pull fails if Odoo does not come up healthy.
set -euo pipefail
cd "$(dirname "$0")"
SSH_HOST="${SSH_HOST:-root@rylai}"
APP_UUID="${APP_UUID:-qcx1w6nrzvfsagjemdd4t6aa}"
DB="${DB:-proto}"
dc() { docker compose -f docker-compose.dev.yaml "$@"; }
[[ -f .env ]] || cp .env.example .env

remote_db=$(ssh "$SSH_HOST" "docker ps -qf name=^db-$APP_UUID")
remote_odoo=$(ssh "$SSH_HOST" "docker ps -qf name=^odoo-$APP_UUID")

echo ">>> snapshot from $SSH_HOST"
mkdir -p .dev
ssh "$SSH_HOST" "docker exec $remote_db pg_dump -U odoo -Fc $DB" > ".dev/$DB.dump"
ssh "$SSH_HOST" "docker exec $remote_odoo tar -C /var/lib/odoo/filestore -cf - $DB" > .dev/filestore.tar

echo ">>> restore"
dc stop odoo 2>/dev/null || true
dc up -d --wait db
dc exec -T db dropdb -U odoo --if-exists "$DB"
dc exec -T db createdb -U odoo "$DB"
dc exec -T db pg_restore -U odoo --no-owner -d "$DB" < ".dev/$DB.dump"
dc run --rm --no-deps --user root -v "$PWD/.dev:/snap:ro" --entrypoint bash odoo -c \
  "rm -rf /var/lib/odoo/filestore/$DB && mkdir -p /var/lib/odoo/filestore \
   && tar -C /var/lib/odoo/filestore -xf /snap/filestore.tar && chown -R odoo:odoo /var/lib/odoo"

echo ">>> neutralize (entrypoint.sh upgrades, then neutralizes, before Odoo serves)"
echo "env['res.users'].browse(2).password = 'admin'; env.cr.commit()" | dc run --rm -T -e AUTO_UPDATE_DB= odoo odoo shell -d "$DB" --no-http --log-level=warn
dc up -d odoo
for _ in $(seq 150); do curl -sf http://localhost:8069/web/health >/dev/null && break; sleep 2; done
curl -sf http://localhost:8069/web/health >/dev/null || { echo "odoo did not become healthy, see: docker compose -f docker-compose.dev.yaml logs odoo" >&2; exit 1; }
echo ">>> http://localhost:8069 (db $DB, login admin / admin; other users keep their deployed passwords)"
