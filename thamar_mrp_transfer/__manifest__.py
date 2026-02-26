{
    'name': 'Thamar MRP Transfer',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Add components to MO with internal transfer',
    'description': """
        Adds a button to Manufacturing Orders to add a component and create an internal transfer from a selected location.
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['mrp', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/mrp_internal_transfer_wizard_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
