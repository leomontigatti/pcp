#!/usr/bin/env bash
# Inject secrets that Odoo only reads from its config file, then hand over to the stock entrypoint.
set -euo pipefail
if [ -n "${ADMIN_PASSWD:-}" ]; then
  sed -i "s|^admin_passwd = .*|admin_passwd = ${ADMIN_PASSWD}|" /etc/odoo/odoo.conf
fi
# Database connection for click-odoo-update; the stock entrypoint then uses the same PG* variables.
export PGHOST="${HOST:-db}" PGPORT="${PORT:-5432}" PGUSER="${USER:-odoo}" PGPASSWORD="${PASSWORD:-odoo}"
# Upgrade changed addons before serving: click-odoo-update hashes each installed module and runs -u
# only for those whose code differs from the last update. The serving service sets AUTO_UPDATE_DB;
# one-off `docker compose run`s leave it empty. A failed upgrade stops the container instead of
# serving a half-upgraded database.
if [ -n "${AUTO_UPDATE_DB:-}" ]; then
  wait-for-psql.py --timeout=30
  click-odoo-update -c /etc/odoo/odoo.conf -d "$AUTO_UPDATE_DB" --if-exists
  # Copies of the deployed data (dev stack) set NEUTRALIZE=1. It runs after every upgrade because
  # -u reloads module data: it re-enabled crons and restored the real ARCA URLs when it ran first.
  if [ "${NEUTRALIZE:-0}" = 1 ]; then
    odoo neutralize -c /etc/odoo/odoo.conf -d "$AUTO_UPDATE_DB" --log-level=warn
    off=http://127.0.0.1:9/dev-disabled
    if [ "$(psql -d "$AUTO_UPDATE_DB" -Atc "select to_regclass('l10n_ar_fiscal_ws') is not null")" = t ]; then
      psql -d "$AUTO_UPDATE_DB" -v ON_ERROR_STOP=1 -qc \
        "update l10n_ar_fiscal_ws set production_url = '$off', homologation_url = '$off'"
      live=$(psql -d "$AUTO_UPDATE_DB" -Atc \
        "select count(*) from l10n_ar_fiscal_ws where '$off' not in (production_url, homologation_url) or production_url <> homologation_url")
      [ "$live" = 0 ] || { echo "neutralize: $live ARCA web service URLs still live, refusing to start" >&2; exit 1; }
    fi
    echo "neutralize: $AUTO_UPDATE_DB neutralized (crons and mail off, ARCA URLs -> $off)" >&2
  fi
fi
exec /entrypoint.sh "$@"
