# -*- coding: utf-8 -*-
{
    'name': 'تقارير تحليل الحسابات - Account Analysis Reports',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Compound entry analysis and running ledger reports per account with date range',
    'description': """
        Account Analysis Reports
        ========================
        Two report types selectable via wizard radio button:

        1. **Compound Entry Analysis (تقرير تحليل مصادر ومصارف الحساب)**
           - Inflow/Outflow grouping by counterpart accounts
           - Debit/Credit nature detection based on account type

        2. **Running Ledger Statement (كشف الحساب بالرصيد المتتابع)**
           - Opening balance, period detail, closing balance
           - Row-by-row cumulative running balance
           - Summary metric cards

        Both reports support multi-account selection with per-account page breaks.
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/journal_summary_wizard_views.xml',
        'report/journal_summary_report_action.xml',
        'report/journal_summary_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
