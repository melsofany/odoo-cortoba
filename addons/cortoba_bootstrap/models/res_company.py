import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

EGYPT_COUNTRY_XMLID = "base.eg"
EGP_CURRENCY_XMLID = "base.EGP"
CHART_TEMPLATE_CODE = "eg"

# The taxes the RFQ bridge applies to its documents.
REQUIRED_TAXES = (
    "eg_standard_sale_14",
    "eg_standard_purchase_14",
    "eg_withholding_3_sale",
    "eg_withholding_3_purchase",
)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def cortoba_bootstrap(self):
        """Apply the Egyptian accounting setup to every company. Idempotent."""
        for company in self.search([]):
            company._cortoba_configure()
        return True

    def _cortoba_configure(self):
        self.ensure_one()
        self._cortoba_set_currency()
        self._cortoba_set_fiscal_country()
        self._cortoba_load_chart()
        self._cortoba_enable_taxes()

    def _cortoba_set_currency(self):
        egp = self.env.ref(EGP_CURRENCY_XMLID, raise_if_not_found=False)
        if not egp:
            _logger.warning("cortoba: EGP currency not found, skipping")
            return
        # Never touch the currency once journal entries exist: Odoo forbids it
        # and the data would be inconsistent.
        if self.currency_id == egp:
            return
        if self.env["account.move.line"].search_count([("company_id", "=", self.id)], limit=1):
            _logger.warning("cortoba: company %s already has journal entries; leaving currency as-is", self.id)
            return
        self.currency_id = egp
        _logger.info("cortoba: company %s currency set to EGP", self.id)

    def _cortoba_set_fiscal_country(self):
        egypt = self.env.ref(EGYPT_COUNTRY_XMLID, raise_if_not_found=False)
        if not egypt:
            _logger.warning("cortoba: Egypt country not found, skipping")
            return
        if self.country_id != egypt:
            self.country_id = egypt
        if self.account_fiscal_country_id != egypt:
            self.account_fiscal_country_id = egypt
        _logger.info("cortoba: company %s country/fiscal country set to Egypt", self.id)

    def _cortoba_load_chart(self):
        chart = self.env["account.chart.template"].with_company(self)
        if CHART_TEMPLATE_CODE not in chart._get_chart_template_mapping():
            _logger.warning("cortoba: chart template %s unavailable", CHART_TEMPLATE_CODE)
            return
        if self.chart_template == CHART_TEMPLATE_CODE:
            _logger.info("cortoba: company %s already uses chart %s", self.id, CHART_TEMPLATE_CODE)
            return
        # Odoo auto-loads a generic chart when `account` is installed before the
        # company country is set, so the Egyptian taxes never get created. The
        # chart can be replaced in place, but only while no entries exist.
        if self.root_id._existing_accounting():
            _logger.warning(
                "cortoba: company %s has accounting data; not replacing chart %s",
                self.id,
                self.chart_template,
            )
            return
        previous = self.chart_template
        try:
            chart.try_loading(CHART_TEMPLATE_CODE, company=self, install_demo=False)
        except Exception:
            _logger.exception("cortoba: failed to load chart %s", CHART_TEMPLATE_CODE)
            return
        _logger.info(
            "cortoba: company %s loaded chart %s (was %s)",
            self.id,
            CHART_TEMPLATE_CODE,
            previous,
        )

    def _cortoba_enable_taxes(self):
        for tax_xmlid in REQUIRED_TAXES:
            tax = self.env.ref("l10n_eg.%s" % tax_xmlid, raise_if_not_found=False)
            if not tax:
                _logger.warning("cortoba: tax %s not found", tax_xmlid)
                continue
            if not tax.active:
                tax.active = True
        _logger.info("cortoba: company %s tax set verified", self.id)
