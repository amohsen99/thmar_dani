# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class JournalSummaryWizard(models.TransientModel):
    _name = 'journal.summary.wizard'
    _description = 'Account Analysis Report Wizard'

    report_type = fields.Selection(
        selection=[
            ('compound_entry', 'تقرير تحليل مصادر ومصارف الحساب - المجمع'),
            ('running_ledger', 'تقرير كشف الحساب التفصيلي بالرصيد المتتابع'),
        ],
        string='نوع التقرير',
        required=True,
        default='compound_entry',
    )
    account_ids = fields.Many2many(
        comodel_name='account.account',
        string='الحسابات',
        required=True,
        help='Select one or more accounts to include in the report.',
    )
    date_from = fields.Date(
        string='من تاريخ',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='إلى تاريخ',
        required=True,
        default=fields.Date.context_today,
    )

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_to < wizard.date_from:
                raise ValidationError(
                    'تاريخ النهاية يجب أن يكون مساوياً أو بعد تاريخ البداية.\n'
                    'The end date must be equal to or after the start date.'
                )

    def action_print_report(self):
        """Generate the Account Analysis PDF report."""
        self.ensure_one()
        data = {
            'report_type': self.report_type,
            'account_ids': self.account_ids.ids,
            'date_from': fields.Date.to_string(self.date_from),
            'date_to': fields.Date.to_string(self.date_to),
        }
        return self.env.ref(
            'thamar_journal_summary.action_report_journal_summary'
        ).report_action(self, data=data)
