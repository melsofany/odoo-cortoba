# odoo-cortoba

Odoo 18 Community for Cortoba Supplies. It runs as a **Render Private Service** and is the accounting engine behind the RFQ app (`cortoba-rfq`). Users never open Odoo directly — the RFQ portal is the only UI, and it reads Odoo through the api-server's accounts bridge.

## Layout

- `Dockerfile` — based on `odoo:18.0`, with a corrected entrypoint.
- `entrypoint.sh` — replaces the stock entrypoint (see "The `PORT` collision" below).
- `odoo.conf` — Odoo server configuration.
- `addons/cortoba_bootstrap/` — one-time, idempotent setup of the company for the RFQ bridge (currency, country, chart, taxes, service user).

## The `PORT` collision (why this repo has its own entrypoint)

Odoo's stock Docker entrypoint reads the environment like this:

```sh
: ${PORT:=${DB_PORT_5432_TCP_PORT:=${PGPORT:=5432}}}
check_config "db_port" "$PORT"
```

So it treats **`PORT` as the Postgres port**. Render also sets `PORT`, but for a different purpose: it is the **HTTP** port Render routes to. On a Render deploy both variables are the same name, so the stock image makes Odoo dial Postgres on the port Render picked for HTTP and the database connection fails.

`entrypoint.sh` fixes this by never reading `PORT` for the database:

- The DB port is `ODOO_DB_PORT`, defaulting to `5432` (Render Postgres listens on 5432).
- The HTTP server binds `http_port` from `odoo.conf`, which is **10000**. Render assigns the internal port and ignores an explicit `openPorts` override, so the config must match it.

## Render setup (manual, from the dashboard)

Render's API/MCP tools cannot create private services, disks, or database-linked env vars, so this part is done by hand:

1. **New > Private Service > Docker**
   - Repository: `melsofany/odoo-cortoba`, branch `main`
   - Region: **Oregon**, Instance type: **Standard**
2. **Disk**: 5 GB, mount path `/var/lib/odoo`
3. **Environment variables**:
   - **Add from database** → select `odoo-db` (`dpg-dbh9nb88v5cc73frro20-a`). This adds `HOST`, `PORT`, `USER`, `PASSWORD`, `DB_NAME` as Render shows them.
   - Because of the collision above, `PORT` is ignored by Odoo. Do **not** remove it — Render may require it for the database link — just leave it; the entrypoint uses `ODOO_DB_PORT` (5432) instead.
   - Add `DB_NAME` = the Odoo database name (e.g. `odoo_db_z2ym`) so Odoo is restricted to it.
   - Add `ODOO_BRIDGE_PASSWORD` (the JSON-RPC password for the `rfq-bridge` service user). It is read at install time and never logged or committed.
4. **Module install/upgrade**:
   - First boot: `ODOO_INIT_MODULES=base,account,l10n_eg,purchase,sale_management` creates the database and installs the apps. Remove it afterwards.
   - To (re)apply the company setup: `ODOO_UPGRADE_MODULES=cortoba_bootstrap`. The setup is idempotent, so this is safe to re-run; remove it afterwards.

> Never point Odoo at `cortoba-rfq-db` (`dpg-d894l13bc2fs73eqr71g-a`). The only database Odoo may use is `odoo-db`.

### Verifying

After the deploy, the service logs should show Odoo starting and the database connection succeeding, e.g. `HTTP service (werkzeug) running on ...:10000` and `Modules loaded`. The service must remain **private** (no `onrender.com` URL).

## Database: Egyptian localization (Task B)

- Database name: `odoo_db_z2ym`.
- Apps installed: **Accounting** (`account`), **Invoicing**, **Purchase** (`purchase`), **Sales** (`sale_management`), and the **Egyptian localization** (`l10n_eg`).
- Company currency: **EGP**; fiscal country: **Egypt**; chart of accounts: the Egyptian one (`eg`).
- `cortoba_bootstrap` sets all of the above and creates the `rfq-bridge` JSON-RPC user. Confirmed in the service logs:
  - `company 1 currency set to EGP`
  - `company 1 loaded chart eg`
  - `company 1 VAT 14% and withholding 3% taxes verified`
  - `bridge user rfq-bridge is ready`
- The 14% standard rates are `eg_standard_sale_14` (sales) and `eg_standard_purchase_14` (purchases); withholding is `eg_withholding_3_sale` / `eg_withholding_3_purchase`. Because the chart is loaded as company data, these records carry external IDs of the form `account.<company>_<id>` (e.g. `account.1_eg_standard_sale_14`), not `l10n_eg.<id>`.

> Note: Odoo installs `account` before the company country is set, so it auto-loads the generic chart first. `cortoba_bootstrap` replaces it with the Egyptian chart while no entries exist; if entries ever exist it leaves the chart alone and logs a warning.

### What is missing in Community

These are **not** usable in Odoo 18 Community and are noted here for the record:

| Report | Module | Availability |
| --- | --- | --- |
| VAT Return (form 10) | `l10n_eg` (`account.report`) | **Definition ships but cannot render** — it depends on the Enterprise-only `account_reports` engine (the `account.report` model is not in Community; the addon returns 404). The bridge computes the VAT figures itself instead. |
| ETA e-invoicing | `l10n_eg_edi_eta` | **Ships in Community** (LGPL-3, depends on `account_edi` + `l10n_eg`) and can be installed, but it submits to the real Egyptian Tax Authority portal, which needs production ETA credentials. Not enabled here. |

So the Community deployment gives us the Egyptian chart of accounts, 14% VAT, and withholding — but the official form-10 VAT return layout and ETA submission are handled by the RFQ bridge / manual filing instead.
