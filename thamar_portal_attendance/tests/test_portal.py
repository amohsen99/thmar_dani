from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestAttendancePortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = cls.env['res.users'].create([
            {'name': name, 'login': 'attendance_' + name, 'password': 'attendance_test',
             'tz': 'Africa/Cairo',
             'group_ids': [Command.set(cls.env.ref('base.group_portal').ids)]}
            for name in ('owner', 'other', 'unlinked')
        ])
        cls.employees = cls.env['hr.employee'].create([
            {'name': user.name, 'user_id': user.id, 'company_id': cls.env.company.id}
            for user in cls.users[:2]
        ])
        cls.records = cls.env['hr.attendance'].create([
            {'employee_id': employee.id, 'check_in': '2026-01-05 22:30:00',
             'check_out': '2026-01-06 06:00:00'} for employee in cls.employees
        ])

    def test_ownership_filters_and_home(self):
        self.authenticate(self.users[0].login, 'attendance_test')
        own = 'data-attendance-id="%s"' % self.records[0].id
        other = 'data-attendance-id="%s"' % self.records[1].id
        response = self.url_open('/my/attendance?employee_id=%s' % self.employees[1].id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(own, response.text)
        self.assertNotIn(other, response.text)
        self.assertIn('2026-01-06 00:30', response.text)
        response = self.url_open('/my/attendance?month=2026-01')
        self.assertIn(own, response.text)
        response = self.url_open('/my/attendance?month=2025-12')
        self.assertNotIn(own, response.text)
        response = self.url_open('/my/attendance?status=open')
        self.assertNotIn(own, response.text)
        response = self.url_open('/my/attendance?month=invalid')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(own, response.text)
        response = self.url_open('/my/home')
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/my/attendance"', response.text)

    def test_unlinked_and_anonymous(self):
        self.authenticate(self.users[2].login, 'attendance_test')
        response = self.url_open('/my/attendance')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('data-attendance-id=', response.text)
        self.authenticate(None, None)
        response = self.url_open('/my/attendance')
        self.assertIn('/web/login', response.url)

    def test_pagination_and_open_records(self):
        from datetime import datetime, timedelta

        self.env['hr.attendance'].create([
            {'employee_id': self.employees[0].id,
             'check_in': datetime(2025, 1, 1, 8) + timedelta(days=day),
             'check_out': datetime(2025, 1, 1, 16) + timedelta(days=day)}
            for day in range(21)
        ])
        opened = self.env['hr.attendance'].create({
            'employee_id': self.employees[0].id, 'check_in': '2026-01-07 08:00:00',
        })
        self.authenticate(self.users[0].login, 'attendance_test')
        response = self.url_open('/my/attendance')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.count('data-attendance-id='), 20)
        response = self.url_open('/my/attendance/page/2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.count('data-attendance-id='), 3)
        response = self.url_open('/my/attendance?status=open')
        self.assertEqual(response.text.count('data-attendance-id='), 1)
        self.assertIn('data-attendance-id="%s"' % opened.id, response.text)

    def test_month_boundaries(self):
        records = self.env['hr.attendance'].create([
            {'employee_id': self.employees[0].id, 'check_in': start, 'check_out': end}
            for start, end in [
                ('2025-12-31 21:00:00', '2025-12-31 21:30:00'),
                ('2025-12-31 22:00:00', '2025-12-31 22:30:00'),
                ('2026-01-31 21:00:00', '2026-01-31 21:30:00'),
                ('2026-01-31 22:00:00', '2026-01-31 22:30:00'),
            ]
        ])
        self.authenticate(self.users[0].login, 'attendance_test')
        response = self.url_open('/my/attendance?month=2026-01')
        self.assertEqual(response.status_code, 200)
        for record in records[1:3]:
            self.assertIn('data-attendance-id="%s"' % record.id, response.text)
        for record in records[0] | records[3]:
            self.assertNotIn('data-attendance-id="%s"' % record.id, response.text)
        response = self.url_open('/my/attendance?month=2026-13')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('data-attendance-id=', response.text)
