# -*- coding: utf-8 -*-
{
    'name': 'Thamar Transportation Management',
    'summary': 'Bus routes, vehicle capacity, and employee transportation allocation',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'author': 'Thamar',
    'license': 'Other proprietary',
    # The employee form in this database includes the Certifications page
    # supplied by hr_skills, so load its model fields before inheriting it.
    'depends': ['hr', 'hr_skills'],
    'data': [
        'security/transport_security.xml',
        'security/ir.model.access.csv',
        'views/transport_route_views.xml',
        'views/transport_vehicle_views.xml',
        'views/hr_employee_views.xml',
        'views/transport_vehicle_assign_wizard_views.xml',
        'views/transport_menus.xml',
    ],
    'application': True,
    'installable': True,
}
