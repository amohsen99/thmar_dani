# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PartnerLedgerWizard(models.TransientModel):
    _name = 'partner.ledger.account.wizard'
    _description = 'Partner Ledger by Account Wizard'

    account_ids = fields.Many2many(
        'account.account',
        string='Accounts',
        required=True,
        help='Select one or more accounts to filter the Partner Ledger.',
    )
    date_from = fields.Date(
        string='Start Date',
        help='Leave empty to use the report default.',
    )
    date_to = fields.Date(
        string='End Date',
        help='Leave empty to use the report default.',
    )

    def action_open_report(self):
        """Open the Partner Ledger filtered by the selected accounts."""
        self.ensure_one()
        report = self.env.ref('account_reports.partner_ledger_report')

        ctx = {
            'report_id': report.id,
            'partner_ledger_account_ids': self.account_ids.ids,
        }

        # Pass date range if the user specified it
        if self.date_from and self.date_to:
            ctx['date'] = {
                'date_from': fields.Date.to_string(self.date_from),
                'date_to': fields.Date.to_string(self.date_to),
                'filter': 'custom',
                'mode': 'range',
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'account_report',
            'name': _('Partner Ledger'),
            'context': ctx,
        }
