# -*- coding: utf-8 -*-
{
    'name': 'Al-Omar Account Custom',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Custom fields on account.move for invoice type, permission number and warehouse',
    'description': """
        Al-Omar Account Customization
        ==============================
        - Add invoice/bill type selection (cash/credit)
        - Add permission number field
        - Add warehouse field on invoices and bills
        - Add separate sequences for invoices and bills
    """,
    'author': 'Al-Omar Group',
    'depends': ['account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_sequence_data.xml',
        'views/account_move_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
