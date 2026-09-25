#!/usr/bin/env bash
# Create the prototype database on the deployed instance and install the AR modules.
# Reads .env.proto-secrets (gitignored). Idempotent: skips creation if the db exists.
set -euo pipefail
cd "$(dirname "$0")"
set -a; source .env.proto-secrets; set +a
SSH_HOST="${SSH_HOST:-root@72.60.59.2}"
APP_UUID="${APP_UUID:-qcx1w6nrzvfsagjemdd4t6aa}"

exists=$(curl -s -X POST -H "Content-Type: application/json" "$ODOO_URL/web/database/list" -d '{"jsonrpc":"2.0","method":"call","params":{}}' | python3 -c "import sys,json;print('yes' if '$ODOO_DB' in json.load(sys.stdin).get('result',[]) else 'no')")
if [ "$exists" = "no" ]; then
  echo ">>> creating database $ODOO_DB"
  curl -s -o /tmp/dbcreate.html -w "http=%{http_code}\n" -X POST "$ODOO_URL/web/database/create" \
    --data-urlencode "master_pwd=$ODOO_MASTER_PASSWORD" --data-urlencode "name=$ODOO_DB" \
    --data-urlencode "login=$ODOO_ADMIN_LOGIN" --data-urlencode "password=$ODOO_ADMIN_PASSWORD" \
    --data-urlencode "lang=es_AR" --data-urlencode "country_code=ar" --data-urlencode "phone="
  grep -oiE "error[^<]{0,120}" /tmp/dbcreate.html | head -3 || true
else
  echo ">>> database $ODOO_DB already exists"
fi

echo ">>> installing modules"
ssh -o BatchMode=yes "$SSH_HOST" "c=\$(docker ps -q --filter name=odoo-$APP_UUID); docker exec \$c /entrypoint.sh odoo -c /etc/odoo/odoo.conf -d $ODOO_DB --stop-after-init --no-http \
  -i l10n_ar_fiscal_ws,l10n_ar_tax,point_of_sale,sale_management,stock,purchase 2>&1 | grep -E ' (ERROR|CRITICAL) |Traceback|Modules loaded|loading .* modules' | tail -20"
echo ">>> done: $ODOO_URL/odoo  (login $ODOO_ADMIN_LOGIN)"
