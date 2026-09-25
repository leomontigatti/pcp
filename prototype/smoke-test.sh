#!/usr/bin/env bash
# Local check: build the image, start Postgres, install the AR modules into a scratch db, stop.
# Usage: ./smoke-test.sh   (needs docker)
set -euo pipefail
cd "$(dirname "$0")"
export DB_PASSWORD="${DB_PASSWORD:-smoke}"
trap 'docker compose -p pcp-smoke down -v >/dev/null 2>&1 || true' EXIT
docker compose -p pcp-smoke build odoo
docker compose -p pcp-smoke up -d db
docker compose -p pcp-smoke run --rm --no-deps -e HOST=db -e USER=odoo -e PASSWORD="$DB_PASSWORD" -e ADMIN_PASSWD=smoke odoo \
  odoo -c /etc/odoo/odoo.conf -d smoke --without-demo --stop-after-init \
  -i l10n_ar_fiscal_ws,l10n_ar_tax,point_of_sale,sale_management,stock,purchase \
  --load-language=es_AR 2>&1 | tee /tmp/pcp-smoke.log | grep -E --line-buffered " (ERROR|CRITICAL) |Traceback|Modules loaded|loading .* modules" | tail -40
if grep -qE " (ERROR|CRITICAL) |Traceback" /tmp/pcp-smoke.log; then
  echo "SMOKE TEST FAILED, see /tmp/pcp-smoke.log"; exit 1
fi
echo "SMOKE TEST PASSED"
