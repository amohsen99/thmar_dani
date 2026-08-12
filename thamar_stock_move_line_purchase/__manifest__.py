# -*- coding: utf-8 -*-
{
    'name': 'Stock Move Line - Purchase Info',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Show purchase order line details (price, discount, taxes, total) on stock move line list view',
    'description': """
        Adds computed/related fields from the Purchase Order Line to the Stock Move Line model,
        and displays them as optional columns in the Moves History list view.

        Fields added:
        - Unit Price (from PO Line)
        - Discount (from PO Line)
        - Taxes (from PO Line)
        - Total Amount (computed: qty * price_unit * (1 - discount/100))
    """,
    'author': 'Thamar',
    'depends': ['stock', 'purchase_stock'],
    'data': [
        'views/stock_move_line_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
