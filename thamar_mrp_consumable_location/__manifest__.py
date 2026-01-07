{
    'name': 'Thamar MRP Consumable Location',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Allow editing component location in Manufacturing Orders',
    'description': """
        Enable Editing Component Location
        =================================
        This module allows users to change the source location of components directly 
        in the Manufacturing Order (MO) form. By default, Odoo makes this field read-only.
    """,
    'author': 'Thamar Dani',
    'depends': ['mrp'],
    'data': [
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
