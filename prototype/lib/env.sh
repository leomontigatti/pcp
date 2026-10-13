# shellcheck shell=bash
# Bash twin of lib/env.py: `source lib/env.sh "$@"` loads .env (--target local, the default) or
# .env.deployed (--target deployed). Callers that write set ENV_WRITES=1 first; deployed writes
# then also need --yes-deployed. The URL must agree with the target.
ENV_TARGET=local
_yes=0
_args=("$@")
for ((_i = 0; _i < ${#_args[@]}; _i++)); do
  case "${_args[_i]}" in
    --target=*) ENV_TARGET="${_args[_i]#--target=}" ;;
    --target) ENV_TARGET="${_args[_i + 1]:-}" ;;
    --yes-deployed) _yes=1 ;;
  esac
done
case "$ENV_TARGET" in
  local) _file=.env ;;
  deployed) _file=.env.deployed ;;
  *) echo "unknown --target '$ENV_TARGET' (local|deployed)" >&2; exit 2 ;;
esac
_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/$_file"
[[ -f "$_file" ]] || { echo "${_file##*/} missing: cp .env.example ${_file##*/}" >&2; exit 2; }
set -a; source "$_file"; set +a
_host=$(python3 -I -c 'import sys, urllib.parse; print(urllib.parse.urlparse(sys.argv[1]).hostname)' "$ODOO_URL")
case "$_host" in localhost | 127.0.0.1) _local=local ;; *) _local=deployed ;; esac
if [[ "$_local" != "$ENV_TARGET" ]]; then
  echo "${_file##*/}: ODOO_URL host $_host does not match --target $ENV_TARGET" >&2; exit 2
fi
if [[ "${ENV_WRITES:-0}" == 1 && "$ENV_TARGET" == deployed && "$_yes" != 1 ]]; then
  echo "refusing to write to the deployed instance without --yes-deployed" >&2; exit 2
fi
echo ":: target $ENV_TARGET ($ODOO_URL, db $ODOO_DB)"
unset _yes _args _i _file _host _local
