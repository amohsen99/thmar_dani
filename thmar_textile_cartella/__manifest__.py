# -*- coding: utf-8 -*-
{
    'name': 'الكارتيلات - Textile Cartella',
    'version': '19.0.1.0.0',
    'summary': 'Textile manufacturing cartella cards with barcode generation and QR label printing',
    'description': '''
        Textile Cartella Module (الكارتيلات)
        ======================================
        - Manage finished product master data
        - Manage cartella categories
        - Define blend ratios directly on cartella card (cotton, polyester, lycra)
        - Create and manage cartella cards with auto-generated barcodes
        - Print thermal label reports with QR Code linking to direct record URL
        - Mobile-friendly views for scanning and quick access
    ''',
    'author': 'Thamar',
    'license': 'LGPL-3',
    'category': 'Manufacturing',
    'website': '',
    'depends': ['base', 'web'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Sequences / data
        'data/ir_sequence_data.xml',
        # Views - master data
        'views/cartella_finished_product_views.xml',
        'views/cartella_category_views.xml',
        # Views - core
        'views/cartella_card_views.xml',
        # Public web page (QR scan landing page)
        'views/cartella_card_public_page.xml',
        # Print web page (browser print)
        'views/cartella_card_print_page.xml',
        # Menu
        'views/cartella_menu.xml',
        # Reports
        'report/cartella_label_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
