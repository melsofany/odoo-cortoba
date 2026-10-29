#!/bin/bash
set -e

# Render injects PORT as the HTTP port (default 10000). Odoo's stock entrypoint
# reads PORT as the *Postgres* port, so the stock image makes Odoo dial Postgres
# on 10000 and the deploy fails to connect. This wrapper never reads PORT for the
# database: the DB port is ODOO_DB_PORT (Render Postgres listens on 5432), and
# Odoo's HTTP server binds the fixed port 10000 (see odoo.conf), which is the
# internal port Render gives every private service.
: "${ODOO_DB_PORT:=5432}"
: "${HOST:=db}"
: "${USER:=odoo}"
: "${PASSWORD:=odoo}"

DB_ARGS=(
  --db_host="${HOST}"
  --db_port="${ODOO_DB_PORT}"
  --db_user="${USER}"
  --db_password="${PASSWORD}"
)

# When DB_NAME is set, restrict Odoo to that database only (it also pins the
# database manager to it). Leave it unset to allow creating one.
if [ -n "${DB_NAME}" ]; then
  DB_ARGS+=(--db-filter="^${DB_NAME}\$")
fi

# Wait for Postgres to accept connections before starting the server. The stock
# image ships wait-for-psql.py; fall back to a plain start if it is absent.
if command -v wait-for-psql.py >/dev/null 2>&1; then
  wait-for-psql.py --db_host="${HOST}" --db_port="${ODOO_DB_PORT}" \
    --db_user="${USER}" --db_password="${PASSWORD}" --timeout=60
fi

# Optional module install/upgrade. Set ODOO_INIT_MODULES (e.g.
# "base,account,l10n_eg,purchase,sale_management") to create the database on
# first boot and install those modules. Later, set it to just the modules you
# want to add or refresh (e.g. "cortoba_bootstrap") to install/upgrade them.
# Both -i and -u are idempotent. Remove the variable afterwards so later
# deploys only start the server.
if [ -n "${ODOO_INIT_MODULES}" ] && [ -n "${DB_NAME}" ]; then
  echo "Ensuring modules in ${DB_NAME}: ${ODOO_INIT_MODULES}"
  odoo "${DB_ARGS[@]}" -d "${DB_NAME}" -i "${ODOO_INIT_MODULES}" --without-demo=all --stop-after-init
fi
if [ -n "${ODOO_UPGRADE_MODULES}" ] && [ -n "${DB_NAME}" ]; then
  echo "Upgrading modules in ${DB_NAME}: ${ODOO_UPGRADE_MODULES}"
  odoo "${DB_ARGS[@]}" -d "${DB_NAME}" -u "${ODOO_UPGRADE_MODULES}" --without-demo=all --stop-after-init
fi

# CMD is ["odoo"], and Odoo's CLI takes no bare positional argument — passing it
# through would be parsed as an invalid argument and abort with exit code 2.
# Drop a leading "odoo"/"--" the way the stock entrypoint does.
if [ "${1:-}" = "odoo" ] || [ "${1:-}" = "--" ]; then
  shift
fi

exec odoo "${DB_ARGS[@]}" "$@"
