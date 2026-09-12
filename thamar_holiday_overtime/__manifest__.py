# -*- coding: utf-8 -*-
{
    'name': 'Thamar Holiday Overtime',
    'summary': 'Auto-split validated leave hours into day/night for payroll overtime',
    'description': """
        When employees take overtime leaves (with the Split Day/Night flag enabled
        on the leave type), this module automatically:
        - Splits the leave hours into Day (6 AM – 9 PM) and Night (9 PM – 6 AM)
        - Injects them as salary input lines on the payslip
        - Computes overtime pay via salary rules (1.35x day, 1.70x night)
    """,
    'license': 'Other proprietary',
    'author': 'Thamar',
    'category': 'Human Resources/Payroll',
    'version': '19.0.2.0.0',
    'depends': [
        'hr_payroll',
        'hr_holidays',
    ],
    'data': [
        'data/hr_payroll_data.xml',
        'views/hr_leave_type_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
