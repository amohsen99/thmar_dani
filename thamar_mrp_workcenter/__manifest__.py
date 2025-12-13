# -*- coding: utf-8 -*-
{
    'name': 'Thamar MRP Workcenter Enhancements',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Workcenter quantity tracking and work order dependencies',
    'description': """
        MRP Workcenter Enhancements
        ============================
        - Show running quantity in workcenter (timer started)
        - Show pending quantity in workcenter (not running yet)
        - Add sequence dependency to work orders
        - Prevent starting work order if previous sequence is not done
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['mrp'],
    'data': [
        'views/mrp_workcenter_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

