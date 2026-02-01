{
    'name': 'Thamar MRP MO Operation Templates',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Add multiple operations and quality checks to MO using templates',
    'description': """
        This module allows users to define operation templates and link them directly to Manufacturing Orders (MO).
        This skip the need for BOMs for one-off products.
        Features:
        - Library of Operation Templates.
        - Many2many selection on MO.
        - Automatic creation of Work Orders and Quality Checks.
        - Group Quality Checks by Manufacturing Order.
    """,
    'author': 'Antigravity',
    'depends': ['mrp','quality', 'quality_control', 'quality_mrp', 'mrp_workorder'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_operation_template_views.xml',
        'views/mrp_production_views.xml',
        'views/quality_check_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
