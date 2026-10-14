#!/usr/bin/env bash
# Replace the local dev copy (docker-compose.dev.yaml) with a snapshot of the deployed prototype:
# database and filestore. Read-only on the server.
# The copy is neutralized: crons and mail servers off, and every ARCA web service URL points
# nowhere, so it cannot spend invoice numbers on the real fiscal points.
set -euo pipefail
cd "$(dirname "$0")"
SSH_HOST="${SSH_HOST:-rylai}"
APP_UUID="${APP_UUID:-qcx1w6nrzvfsagjemdd4t6aa}"
DB="${DB:-proto}"
dc() { docker compose -f docker-compose.dev.yaml "$@"; }

remote_db=$(ssh "$SSH_HOST" "docker ps -qf name=^db-$APP_UUID")
remote_odoo=$(ssh "$SSH_HOST" "docker ps -qf name=^odoo-$APP_UUID")

echo ">>> snapshot from $SSH_HOST"
mkdir -p .dev
ssh "$SSH_HOST" "docker exec $remote_db pg_dump -U odoo -Fc $DB" > .dev/$DB.dump
ssh "$SSH_HOST" "docker exec $remote_odoo tar -C /var/lib/odoo/filestore -cf - $DB" > .dev/filestore.tar

echo ">>> restore"
dc stop odoo 2>/dev/null || true
dc up -d --wait db
dc exec -T db dropdb -U odoo --if-exists "$DB"
dc exec -T db createdb -U odoo "$DB"
dc exec -T db pg_restore -U odoo --no-owner -d "$DB" < .dev/$DB.dump
dc run --rm --no-deps --user root -v "$PWD/.dev:/snap:ro" --entrypoint bash odoo -c \
  "rm -rf /var/lib/odoo/filestore/$DB && mkdir -p /var/lib/odoo/filestore \
   && tar -C /var/lib/odoo/filestore -xf /snap/filestore.tar && chown -R odoo:odoo /var/lib/odoo"

echo ">>> neutralize"
dc run --rm odoo odoo neutralize -d "$DB"
dc exec -T db psql -U odoo -d "$DB" -c \
  "UPDATE l10n_ar_fiscal_ws SET production_url = 'http://127.0.0.1:9/dev-disabled', homologation_url = 'http://127.0.0.1:9/dev-disabled'"

dc up -d odoo
echo ">>> http://localhost:8069 (db $DB, same logins as the deployed instance)"
