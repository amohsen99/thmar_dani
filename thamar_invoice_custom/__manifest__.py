# -*- coding: utf-8 -*-
{
    'name': 'Thamar Invoice Customization',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Custom invoice and payment workflow with signatures and amount in words',
    'description': """
        Invoice and Payment Customization Module
        ========================================
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['account', 'web'],
    'data': [
        'security/payment_security.xml',
        'security/ir.model.access.csv',
        'views/account_payment_view.xml',
        'views/report_payment_receipt.xml',
        'views/report_payment_action.xml',
        'views/report_custom.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

