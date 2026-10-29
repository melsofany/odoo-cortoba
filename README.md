# odoo-cortoba

Odoo 18 Community for Cortoba Supplies. It runs as a private Render service and is the accounting engine behind the RFQ app (`cortoba-rfq`). Users never open Odoo directly.

## Layout

- `Dockerfile` — based on `odoo:18.0`.
- `odoo.conf` — Odoo server configuration.
- `addons/` — custom modules (VAT report, RFQ bridge).

## Render setup (manual, from the dashboard)

- Type: **Private Service**, runtime Docker, this repo, branch `main`, region Oregon, plan Standard.
- Disk: 5 GB, mount path `/var/lib/odoo`.
- Environment variables (values from the `odoo-db` Postgres instance):
  - `HOST`, `PORT`, `USER`, `PASSWORD`, `DB_NAME` as provided by Render's connection info.
