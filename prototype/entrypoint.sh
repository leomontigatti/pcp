#!/usr/bin/env bash
# Inject secrets that Odoo only reads from its config file, then hand over to the stock entrypoint.
set -euo pipefail
if [ -n "${ADMIN_PASSWD:-}" ]; then
  sed -i "s|^admin_passwd = .*|admin_passwd = ${ADMIN_PASSWD}|" /etc/odoo/odoo.conf
fi
exec /entrypoint.sh "$@"
