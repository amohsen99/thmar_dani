{
    'name': 'Thamar Logistics',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Logistics',
    'summary': 'Import Shipment & Contract Management',
    'description': 'Manage import contracts, shipments (ACID), and containers '
                   'for the logistics department.',
    'author': 'Thamar',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/logistics_contract_views.xml',
        'views/logistics_shipment_views.xml',
        'views/logistics_config_views.xml',
        'views/logistics_menus.xml',
    ],
    'installable': True,
    'application': True,
}
