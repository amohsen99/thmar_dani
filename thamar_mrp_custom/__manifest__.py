{
    'name': 'Thamar MRP Custom',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Custom Manufacturing Order fields and enhancements',
    'description': """
        Manufacturing Order Customization Module
        =========================================
        - Add Partner field to Manufacturing Orders
        - Add Sale Order field to Manufacturing Orders
        - Enhanced shop floor timer to show days, hours, minutes, seconds
        - Add Features tab with Color, Design, Width, Weight, Density, and Average fields
        - Color and Design configuration menus
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['mrp', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_color_views.xml',
        'views/mrp_design_views.xml',
        'views/mrp_production_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'thamar_mrp_custom/static/src/widgets/timer.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

