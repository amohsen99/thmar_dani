{
    'name': 'Thamar Product Barcode Generator',
    'version': '1.0.0',
    'summary': 'Auto-generate product barcodes from category and variants',
    'description': '''
        Automatic Barcode Generation for Products
        ==========================================
        
        This module automatically generates barcodes for product variants based on:
        - Category Code (from product category)
        - Color Code (4 characters)
        - Design Code (4 characters)
        - Grade Code (1 character)
        - Type Code (Printing/Drying)
        
        Barcode Structure: CATEGORYCOLORDESIGNGRADETYP
        Example: 01000100011P (Category:01, Color:0001, Design:0001, Grade:1, Type:P)
    ''',
    'author': 'Thamar Dani',
    'license': 'LGPL-3',
    'category': 'Inventory/Inventory',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/product_attribute_data.xml',
        # 'data/color_data.xml',
        'data/color/color_blue.xml',
        'views/product_category_views.xml',
        'views/product_attribute_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

