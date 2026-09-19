# -*- coding: utf-8 -*-
{
    'name': 'Thamar Holiday Overtime',
    'summary': 'Department-approved overtime requests, work entries and payroll',
    'description': """
        Dedicated overtime requests with department supervisor then manager approval.
        Approved requests generate linked work entries and payroll allowances for
        holiday days, day/night hours and weekly-rest/public-holiday hours.
        Legacy leave-based overtime remains supported for existing records.
    """,
    'license': 'Other proprietary',
    'author': 'Thamar',
    'category': 'Human Resources/Payroll',
    'version': '19.0.4.0.0',
    'depends': [
        'hr_payroll',
        'hr_holidays',
        'thamar_hr_leaves',
    ],
    'data': [
        'security/overtime_security.xml',
        'security/ir.model.access.csv',
        'data/overtime_data.xml',
        'data/hr_payroll_data.xml',
        'views/overtime_views.xml',
        'views/hr_leave_type_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': 'post_init_hook',
}
