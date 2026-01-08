{
    'name': 'Thamar Employee Custom',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Custom Employee Payroll Fields',
    'description': """
        Employee Payroll Customization Module
        =====================================
        - Add custom payroll fields to employee form
        - Previous Wage (Float)
        - Promotion Amount (Float)
        - Increase Rate (Float)
        - Fixed Allowances (Float)
        -fdsaf
        - Tax Personal Exemption (الإعفاء الشخصي السنوي)
        - Tax Family Exemption (الإعفاءات العائلية السنوية)
        - All fields grouped in Payroll tab
    """,
    'author': 'Thamar Dani',
    'website': 'https://www.thamardani.com',
    'depends': ['hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

