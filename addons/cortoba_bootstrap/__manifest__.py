{
    "name": "Cortoba Odoo Bootstrap",
    "summary": "One-time, idempotent configuration of the Odoo company for the RFQ bridge.",
    "description": """
Configures the Egyptian accounting setup the RFQ bridge expects:

- company currency EGP and fiscal country Egypt;
- the Egyptian chart of accounts (l10n_eg) loaded;
- the 14% VAT and 3% withholding taxes enabled for sale and purchase.

Everything is idempotent: the hooks only act when the value is not already set,
so the module can stay installed and re-run on every deploy without side
effects.
""",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "author": "Cortoba Supplies",
    "category": "Accounting/Localizations",
    "depends": ["account", "l10n_eg", "purchase", "sale_management"],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}
