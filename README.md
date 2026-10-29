# odoo-cortoba

Odoo 18 Community for Cortoba Supplies. It runs as a **Render Private Service** and is the accounting engine behind the RFQ app (`cortoba-rfq`). Users never open Odoo directly — the RFQ portal is the only UI, and it reads Odoo through the api-server's accounts bridge.

## Layout

- `Dockerfile` — based on `odoo:18.0`, with a corrected entrypoint.
- `entrypoint.sh` — replaces the stock entrypoint (see "The `PORT` collision" below).
- `odoo.conf` — Odoo server configuration.
- `addons/` — custom modules (RFQ bridge helpers).

## The `PORT` collision (why this repo has its own entrypoint)

Odoo's stock Docker entrypoint reads the environment like this:

```sh
: ${PORT:=${DB_PORT_5432_TCP_PORT:=${PGPORT:=5432}}}
check_config "db_port" "$PORT"
```

So it treats **`PORT` as the Postgres port**. Render also sets `PORT`, but for a different purpose: it is the **HTTP** port Render routes to (default `10000`). On a Render deploy both variables are the same name, so the stock image makes Odoo dial Postgres on port `10000` and the database connection fails.

`entrypoint.sh` fixes this by never reading `PORT` for the database:

- The DB port is `ODOO_DB_PORT`, defaulting to `5432` (Render Postgres listens on 5432).
- The HTTP server binds the fixed port `8069` from `odoo.conf` (`http_port`), not `PORT`.

Render forwards traffic to the port the process binds, so binding 8069 is fine; `PORT` is simply ignored by Odoo.

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
4. **First run only**: add `ODOO_INIT_MODULES=base,l10n_eg` to create the database and install the Egyptian localization on the first boot, then **remove it** so later deploys only start the server.

> Never point Odoo at `cortoba-rfq-db` (`dpg-d894l13bc2fs73eqr71g-a`). The only database Odoo may use is `odoo-db`.

### Verifying

After the deploy, the service logs should show Odoo starting and the database connection succeeding, e.g. `database connection ... OK` / `Modules loaded`. The service must remain **private** (no `onrender.com` URL).

## Database: Egyptian localization (Task B)

- Database name: `odoo_db_z2ym` (or the name Render provides).
- Apps to install: **Accounting** (`account`), **Invoicing**, **Purchase**, **Sales**, and the **Egyptian localization** (`l10n_eg`).
- Company currency: **EGP**; fiscal country: **Egypt**.
- `l10n_eg` is `auto_install` on `account`, so installing Accounting pulls it in. It provides the chart of accounts, taxes, fiscal positions, and the **VAT Return** report definition.
- The 14% standard rates are `eg_standard_sale_14` (sales) and `eg_standard_purchase_14` (purchases). Withholding tax is provided by the localization's withholding tax report.

### What is missing in Community

These are **not** usable in Odoo 18 Community and are noted here for the record:

| Report | Module | Availability |
| --- | --- | --- |
| VAT Return (form 10) | `l10n_eg` (`account.report`) | **Definition ships but cannot render** — it depends on the Enterprise-only `account_reports` engine (the `account.report` model is not in Community). The bridge computes the VAT figures itself instead. |
| ETA e-invoicing | `l10n_eg_edi_eta` | **Ships in Community** (LGPL-3, depends on `account_edi` + `l10n_eg`) and can be installed, but it submits to the real Egyptian Tax Authority portal, which needs production ETA credentials. Not enabled here. |

So the Community deployment gives us the Egyptian chart of accounts, 14% VAT, and withholding — but the official form-10 VAT return layout and ETA submission are handled by the RFQ bridge / manual filing instead.
