{
    'name': 'Purchase Custom Edit',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Customize the Purchase Order form and behavior',
    'description': 'Adds custom fields and logic to Purchase Orders.',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_inherit_view.xml',
    ],
    'installable': True,
    'application': False,
}
