{
    'name': 'Thamar Warehouse Custom Access',
    'version': '1.0.0',
    'summary': 'Warehouse manager/keeper per warehouse with restricted access',
    'description':
    'Add manager and keeper to warehouses and restrict access to warehouse '
    'data so users see only their warehouse. '
    'Manager is the only one allowed to validate pickings.',
    'author': 'Generated for Mohsen',
    'license': 'LGPL-3',
    'category': 'Inventory/Inventory',
    'depends': ['stock'],
    'data': [
    'security/security.xml',
    'security/ir.model.access.csv',
    'views/warehouse_views.xml',
    ],
    'installable': True,
    'application': False,
}