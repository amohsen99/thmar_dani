# -*- coding: utf-8 -*-

from odoo import models


class AccountPartnerLedgerReportHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        """Extend to support filtering by specific account IDs.

        When ``partner_ledger_account_ids`` is present in the
        options (injected by the wizard via context), we:
        1. Persist the list in options so it survives page navigation.
        2. Inject an ``account_id`` domain into ``forced_domain``.
        3. Remove the account_type filter (receivable/payable) because
           the user may select accounts of any type.
        4. Auto-unfold all partners so initial balances are visible.
        """
        super()._custom_options_initializer(report, options, previous_options)

        # Pick up account IDs from context (first open) or persisted options
        account_ids = (
            previous_options.get('partner_ledger_account_ids')
            or options.get('partner_ledger_account_ids')
        )

        if account_ids:
            options['partner_ledger_account_ids'] = account_ids

            # Inject into forced_domain
            options['forced_domain'] = (
                options.get('forced_domain', [])
                + [('account_id', 'in', account_ids)]
            )

            # Disable the receivable/payable type filter — we want to
            # show entries for the specific accounts regardless of type.
            options.pop('account_type', None)

            # Auto-expand every partner so initial balances are visible
            # without the user needing to click "Unfold All".
            options['unfold_all'] = True
