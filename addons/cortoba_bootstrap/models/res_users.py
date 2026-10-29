import logging
import os

from odoo import api, models

_logger = logging.getLogger(__name__)

BRIDGE_LOGIN = "rfq-bridge"


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def cortoba_ensure_bridge_user(self):
        """Create/refresh the JSON-RPC service user the RFQ bridge logs in as.

        The password comes from ODOO_BRIDGE_PASSWORD in the service environment
        so no secret is ever committed or written to the logs. Re-running is
        safe: the user is looked up by login and only its groups/password are
        refreshed.
        """
        password = os.environ.get("ODOO_BRIDGE_PASSWORD")
        if not password:
            _logger.warning(
                "cortoba: ODOO_BRIDGE_PASSWORD is not set; skipping bridge user"
            )
            return False

        login = os.environ.get("ODOO_BRIDGE_LOGIN", BRIDGE_LOGIN)
        user = self.sudo().search([("login", "=", login)], limit=1)

        # Accounting rights are what the bridge needs: create/post invoices,
        # bills, payments and journal entries.
        group_refs = [
            "account.group_account_manager",
            "account.group_account_user",
            "base.group_partner_manager",
        ]
        groups = [
            self.env.ref(ref).id
            for ref in group_refs
            if self.env.ref(ref, raise_if_not_found=False)
        ]

        values = {
            "login": login,
            "name": "RFQ Bridge",
            "password": password,
            "groups_id": [(6, 0, groups)],
            "active": True,
        }
        if user:
            user.sudo().write(values)
        else:
            user = self.sudo().create(values)
        _logger.info("cortoba: bridge user %s is ready (id=%s)", login, user.id)
        return True
