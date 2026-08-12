# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': "Product Secondary Unit of Measure",
    'version': '19.0.0.0',
    'category':"Extra Tools",
    'summary': "Product secondary UOM Quantity inventory secondary UOM warehouse secondary UOM secondary UOM for product Sale Secondary UOM product stock unit of measurement purchase secondary unit of measures sales order secondary UOM purchase secondary UOM product uom",
    'description': """
       
        Secondary Product UOM Odoo App helps users to managing or converting the secondary unit of measure of the product from a primary unit of measure and vice versa. User can add secondary quantity and secondary unit of measure in sale order, stock picking and purchase order.
    
    """,
    'author': 'BROWSEINFO',
    'website': 'https://www.browseinfo.com/demo-request?app=bi_product_secondary_uom&version=19&edition=Community',
    'depends': ['base','sale_management','stock','purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/stock_quant_view.xml',
        'views/sale_order_line_view.xml',
        'views/purchase_order_line_view.xml',
        'views/stock_move_view.xml',
    ],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://www.browseinfo.com/demo-request?app=bi_product_secondary_uom&version=19&edition=Community',
    "images":['static/description/Banner.gif'],
}

