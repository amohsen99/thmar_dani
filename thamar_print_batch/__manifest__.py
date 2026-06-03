# -*- coding: utf-8 -*-
{
    'name': 'المطبوعات - Payment Print Batches',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Treasury print-batching workflow to manage draft payments before posting',
    'description': """
        Payment Print Batches (المطبوعات)
        ==================================
        - Group draft payments into print batches
        - Bulk validate and post payments
        - Professional QWeb PDF report per batch
        - Contextual action from payment list view
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['account', 'thamar_invoice_custom'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/account_print_batch_views.xml',
        'views/account_payment_views.xml',
        'report/print_batch_report.xml',
        'report/print_batch_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
