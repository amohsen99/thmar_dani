# -*- coding: utf-8 -*-
{
    'name': 'Thamar Bank Statement Receipt',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Print bank statement lines as transaction receipts',
    'description': """
        Bank Statement Receipt Module
        ==============================
        - Print one receipt per selected bank statement / transaction line
        - Arabic RTL layout support
        - Shows: date, label, partner, amount, journal, reconciliation status
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['account', 'account_accountant'],
    'data': [
        'views/report_bank_statement_receipt.xml',
        'views/report_bank_statement_receipt_action.xml',
    ],
    'external_dependencies': {
        'python': ['num2words'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
