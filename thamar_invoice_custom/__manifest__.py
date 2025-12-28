# -*- coding: utf-8 -*-
{
    'name': 'Thamar Invoice Customization',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Custom invoice and payment workflow with approval, signatures and amount in words',
    'description': """
        Invoice and Payment Customization Module
        ========================================
        - Payment approval workflow
        - Cheque payment fields (bank, number, due date)
        - Arabic amount in words
        - Custom payment receipts
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['account', 'web'],
    'data': [
        'security/payment_security.xml',
        'security/ir.model.access.csv',
        'data/res_currency_data.xml',
        'views/account_payment_view.xml',
        'views/report_payment_receipt.xml',
        'views/report_payment_action.xml',
        'views/report_custom.xml',
    ],
    'external_dependencies': {
        'python': ['num2words'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

