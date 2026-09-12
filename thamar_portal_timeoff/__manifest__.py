{
    'name': 'Thamar Portal Time Off',
    'summary': 'Allow portal users to manage their time off requests via an attractive OWL interface',
    'description': """
Portal Time Off Management
==========================
Provides a modern, single-page portal interface for employees with portal access
to create, edit, and delete their time off requests.

Features:
* Beautiful OWL-based dashboard with leave balance cards
* Create / edit / delete time off requests
* Real-time status tracking (Pending, Approved, Refused)
* Glassmorphism design with smooth animations
* Fully responsive layout
    """,
    'author': 'Thamar',
    'category': 'Human Resources',
    'version': '19.0.1.0.2',
    'license': 'Other proprietary',
    'depends': [
        'portal',
        'hr_holidays',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/portal_templates.xml',
    ],
    'assets': {
        # Loaded only by the Time Off portal page. Keeping these assets out of
        # web.assets_frontend prevents this optional application from affecting
        # the login page or other portal pages.
        'thamar_portal_timeoff.assets_timeoff': [
            'thamar_portal_timeoff/static/src/css/timeoff_portal.css',
            'thamar_portal_timeoff/static/src/xml/timeoff_templates.xml',
            'thamar_portal_timeoff/static/src/js/timeoff_service.js',
            'thamar_portal_timeoff/static/src/js/timeoff_stats.js',
            'thamar_portal_timeoff/static/src/js/timeoff_list.js',
            'thamar_portal_timeoff/static/src/js/timeoff_form.js',
            'thamar_portal_timeoff/static/src/js/timeoff_app.js',
        ],
        'thamar_portal_timeoff.assets_employee': [
            'thamar_portal_timeoff/static/src/css/employee_portal.css',
            'thamar_portal_timeoff/static/src/js/employee_portal.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
