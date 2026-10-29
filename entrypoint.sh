#!/bin/bash
set -e

# Render injects PORT as the HTTP port (default 10000). Odoo's stock entrypoint
# reads PORT as the *Postgres* port, so the stock image makes Odoo dial Postgres
# on 10000 and the deploy fails to connect. This wrapper never reads PORT for the
# database: the DB port is ODOO_DB_PORT (Render Postgres listens on 5432), and
# Odoo's HTTP server binds the fixed port 8069 (see odoo.conf).
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

# First-run initialisation. Set ODOO_INIT_MODULES (e.g. "base,l10n_eg") on the
# service to create the database and install those modules on the first boot;
# remove the variable afterwards so later deploys only start the server.
# -i is a no-op for modules that are already installed, but skipping it once the
# database exists keeps restarts fast and avoids re-running the upgrade.
if [ -n "${ODOO_INIT_MODULES}" ] && [ -n "${DB_NAME}" ]; then
  if ! odoo shell -d "${DB_NAME}" --no-http <<'PY' >/dev/null 2>&1
print("ready")
PY
  then
    echo "Initialising database ${DB_NAME} with modules: ${ODOO_INIT_MODULES}"
    odoo "${DB_ARGS[@]}" -d "${DB_NAME}" -i "${ODOO_INIT_MODULES}" --without-demo=all --stop-after-init
  fi
fi

exec odoo "${DB_ARGS[@]}" "$@"
