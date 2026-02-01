{
    'name': 'Thamar MRP Custom',
    'version': '19.0.4.0.0',
    'category': 'Manufacturing',
    'summary': 'Product Features Per Order Line with Auto-sync to Manufacturing Orders',
    'description': """
        Manufacturing Order Customization Module
        =========================================
        - Add Partner field to Manufacturing Orders
        - Add Sale Order field to Manufacturing Orders
        - Enhanced shop floor timer to show days, hours, minutes, seconds
        - Add Features to Products with "Has Features" checkbox
        - Add Features to Sale Order Lines (per product)
        - Each order line can have different features based on its product
        - Color and Design configuration menus
        - Add Features to Manufacturing Orders
        - Auto-sync features: Product → Sale Order Line → Manufacturing Order
        - Each MO gets features from its corresponding sale order line
        - Smart button to view related Manufacturing Orders from Sale Order
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['product','mrp', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_color_category_views.xml',
        'views/mrp_color_views.xml',
        'views/mrp_fabric_type_views.xml',
        'views/mrp_design_views.xml',
        # 'views/mrp_packing_type_views.xml',
        'views/product_template_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_stripe_views.xml'
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

