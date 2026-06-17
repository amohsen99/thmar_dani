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

    # ── Optional column toggles (running ledger) ──
    show_ending_balance = fields.Boolean(
        string='الرصيد النهائي',
        default=True,
        help='Show / hide the Ending Balance metric card and column.',
    )
    show_cheque_number = fields.Boolean(
        string='رقم الشيك',
        default=False,
        help='Show / hide the Cheque Number column.',
    )
    show_bank_name = fields.Boolean(
        string='اسم البنك',
        default=False,
        help='Show / hide the Bank Name column.',
    )
    show_cheque_due_date = fields.Boolean(
        string='تاريخ استحقاق الشيك',
        default=False,
        help='Show / hide the Cheque Due Date column.',
    )
    show_analytic = fields.Boolean(
        string='التحليل التكلفي',
        default=False,
        help='Show / hide the Analytic Account column.',
    )
    show_analytic_distribution = fields.Boolean(
        string='التوزيع التحليلي',
        default=False,
        help='Show / hide the Analytic Distribution column.',
    )
    show_partner_account = fields.Boolean(
        string='حساب العميل/المورد',
        default=False,
        help='Show / hide the partner account column (the account linked to the partner on the move line).',
    )
    show_metric_cards = fields.Boolean(
        string='إظهار بطاقات القياس',
        default=True,
        help='Show / hide the Metric Cards Row.',
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
            # column visibility flags
            'show_ending_balance': self.show_ending_balance,
            'show_cheque_number': self.show_cheque_number,
            'show_bank_name': self.show_bank_name,
            'show_cheque_due_date': self.show_cheque_due_date,
            'show_analytic': self.show_analytic,
            'show_analytic_distribution': self.show_analytic_distribution,
            'show_partner_account': self.show_partner_account,
            'show_metric_cards': self.show_metric_cards,
        }
        if self.report_type == 'running_ledger':
            action_ref = 'thamar_journal_summary.action_report_running_ledger'
        else:
            action_ref = 'thamar_journal_summary.action_report_compound_entry'

        return self.env.ref(action_ref).report_action(self, data=data)
