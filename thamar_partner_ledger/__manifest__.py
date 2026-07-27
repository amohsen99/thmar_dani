# -*- coding: utf-8 -*-
{
    'name': 'Thamar Partner Ledger by Account',
    'summary': 'Filter Partner Ledger by specific accounts with initial balance',
    'description': """
        Extends the Partner Ledger report to allow filtering by
        specific accounts (not just receivable/payable types).
        Shows initial balance for every partner when filtered.
    """,
    'license': 'Other proprietary',
    'author': 'Thamar',
    'category': 'Accounting/Accounting',
    'version': '19.0.1.0.0',
    'depends': ['account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/partner_ledger_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
