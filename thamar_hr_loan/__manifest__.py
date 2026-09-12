# -*- coding: utf-8 -*-
{
    'name': 'Thamar HR Loan',
    'summary': 'Employee loan management with payroll deduction integration',
    'description': """
        Manage employee loans for Thamar:
        - Small Loans: one-time deduction from payslip
        - Long Loans: multi-month installment deductions
        - Manager → HR approval workflow for all loans
        - Automatic payslip deduction via salary rules
    """,
    'license': 'Other proprietary',
    'author': 'Thamar',
    'category': 'Human Resources/Payroll',
    'version': '19.0.1.0.0',
    'depends': [
        'hr_payroll',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_data.xml',
        'views/hr_loan_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
