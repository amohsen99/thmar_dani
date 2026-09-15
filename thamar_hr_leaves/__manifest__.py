# -*- coding: utf-8 -*-
{
    'name': 'Thamar HR Leaves',
    'summary': 'Egyptian Labor Law Leave Management – Dynamic entitlements, auto-allocation & yearly cron',
    'description': """
        Comprehensive leave management module for Thamar:
        - Casual Leave (7 days/year, non-carryover, expires Dec 31)
        - Annual Leave (dynamic computation based on service year, age, experience, hazardous location)
        - Monthly accrual for annual leave
        - Auto-allocation on employee creation
        - Yearly cron job (Jan 1) for recalculation and carryover
        - Transparent readonly entitlement fields on employee form
    """,
    'license': 'Other proprietary',
    'author': 'Thamar',
    'category': 'Human Resources/Time Off',
    'version': '19.0.1.3.0',
    'pre_init_hook': 'pre_init_hook',
    'depends': [
        'hr',
        'hr_holidays',
        # Provides hr.employee.hire_date, the single source of truth for
        # leave eligibility and service duration.
        'thamar_hr_custom',
    ],
    'data': [
        'security/hr_holidays_security.xml',
        'security/ir.model.access.csv',
        'data/leave_type_data.xml',
        'data/leave_type_special_data.xml',
        'data/leave_type_portal_data.xml',
        'data/ir_cron_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_type_approval_views.xml',
        'views/hr_department_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_leave_approval_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
