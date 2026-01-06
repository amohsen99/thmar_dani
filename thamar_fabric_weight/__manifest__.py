# -*- coding: utf-8 -*-
{
    'name': 'Thamar Fabric Weight Tracking',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Track fabrics by both weight and quantity (pieces/rolls)',
    'description': """
        Fabric Weight Tracking Module
        ==============================
        Track fabric products by both quantity (pieces/rolls/tobs) and weight.
        
        Features:
        - Add weight per unit field to products
        - Track weight in Sale Orders (per line and total)
        - Track weight in Purchase Orders (per line and total)
        - Track weight in Stock Moves (Inventory)
        - Track weight in Manufacturing Orders
        - Checkbox on product to enable fabric tracking
        
        Use Case:
        - You sell 10 rolls of fabric, each weighing 25 kg
        - Total: 10 rolls = 250 kg
        - Track both in all transactions
    """,
    'author': 'Thamar',
    'website': 'https://www.thamar.com',
    'depends': [
        'sale',
        'purchase',
        'stock',
        'mrp',
        'product',
    ],
    'data': [
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_quant_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

