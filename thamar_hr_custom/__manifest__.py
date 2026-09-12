# -*- coding: utf-8 -*-
{
    'name': 'Thamar HR Custom',
    'summary': 'Custom HR fields and modifications for Thamar',
    'description': """
        Custom HR module for Thamar:
        - Adds Hire Date field to employee payroll page
    """,
    'license': 'Other proprietary',
    'author': 'Thamar',
    'category': 'Human Resources',
    'version': '19.0.1.0.0',
    'depends': ['hr', 'hr_work_entry', 'hr_work_entry_enterprise', 'hr_work_entry_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_work_entry_views.xml',
        'wizard/batch_generate_work_entries_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
