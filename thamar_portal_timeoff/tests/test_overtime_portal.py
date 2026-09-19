import re

from lxml import html

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestOvertimePortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = cls.env['res.users'].create([
            {'name': label, 'login': 'ot_portal_' + label, 'password': 'ot_portal_test',
             'group_ids': [Command.set(cls.env.ref('base.group_portal').ids)]}
            for label in ('supervisor', 'manager', 'worker', 'outsider')
        ])
        cls.supervisor, cls.manager, cls.worker, cls.outsider = cls.users
        cls.employees = cls.env['hr.employee'].create([
            {'name': user.name, 'user_id': user.id, 'company_id': cls.env.company.id,
             'date_version': '2026-01-01', 'contract_date_start': '2026-01-01', 'wage': 3000}
            for user in cls.users
        ])
        cls.department = cls.env['hr.department'].create({
            'name': 'Portal Overtime Test', 'supervisor_id': cls.employees[0].id,
            'manager_id': cls.employees[1].id,
        })
        cls.employees[:3].department_id = cls.department
        cls.rec = cls.env['thamar.overtime.request'].with_user(cls.supervisor).sudo().create({
            'employee_id': cls.employees[2].id, 'kind': 'holiday_day',
            'date_start': '2026-09-10 08:00:00', 'date_stop': '2026-09-10 16:00:00',
            'reason': 'PORTAL_OVERTIME_VISIBLE_TO_OWNER',
        })
        cls.rec.action_submit()
        cls.mission_rec = cls.env['thamar.overtime.request'].with_user(cls.supervisor).sudo().create({
            'employee_id': cls.employees[2].id, 'kind': 'mission',
            'date_start': '2026-09-11 08:00:00', 'date_stop': '2026-09-11 12:00:00',
            'reason': 'PORTAL_MISSION_VISIBLE_TO_OWNER',
        })
        cls.mission_rec.action_submit()

    def _page(self, user, scope='mine', request_category='overtime'):
        self.authenticate(user.login, 'ot_portal_test')
        base_url = '/my/missions' if request_category == 'mission' else '/my/overtime'
        response = self.url_open(base_url + '?scope=' + scope)
        self.assertEqual(response.status_code, 200, response.text[:1000])
        return response

    def test_employee_read_only_and_outsider_isolation(self):
        response = self._page(self.worker)
        self.assertIn('PORTAL_OVERTIME_VISIBLE_TO_OWNER', response.text)
        self.assertNotIn('PORTAL_MISSION_VISIBLE_TO_OWNER', response.text)
        self.assertNotIn('action="/my/overtime/create"', response.text)

    def test_portal_navigation_has_one_timeoff_entry(self):
        self.authenticate(self.worker.login, 'ot_portal_test')
        response = self.url_open('/my/home')
        self.assertEqual(response.status_code, 200, response.text[:1000])
        self.assertIn('href="/my/timeoff"', response.text)
        self.assertIn('href="/my/overtime"', response.text)
        self.assertIn('href="/my/missions"', response.text)
        self.assertNotIn('href="/my/assignments"', response.text)
        self.assertNotIn('href="/my/team/timeoff"', response.text)

    def test_team_leave_management_is_inside_timeoff_menu(self):
        self.authenticate(self.supervisor.login, 'ot_portal_test')
        response = self.url_open('/my/timeoff')
        self.assertEqual(response.status_code, 200, response.text[:1000])
        self.assertIn('href="/my/timeoff?scope=team"', response.text)
        self.assertIn('o_portal_timeoff_app', response.text)
        self.assertNotIn('o_portal_team_timeoff_app', response.text)

        response = self.url_open('/my/timeoff?scope=team')
        self.assertEqual(response.status_code, 200, response.text[:1000])
        self.assertIn('o_portal_team_timeoff_app', response.text)
        self.assertNotIn('o_portal_timeoff_app"', response.text)

        response = self.url_open('/my/team/timeoff')
        self.assertIn('/my/timeoff?scope=team', response.url)

    def test_manager_only_leave_is_in_the_single_timeoff_feed(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'PORTAL_MANAGER_ONLY_IN_TIMEOFF',
            'requires_allocation': False,
            'manager_only_requests': True,
        })
        leave = self.env['hr.leave'].with_context(
            skip_thamar_leave_policy_checks=True,
        ).create({
            'employee_id': self.employees[2].id,
            'holiday_status_id': leave_type.id,
            'request_date_from': '2026-09-15',
            'request_date_to': '2026-09-15',
        })
        payload = self.env['hr.leave'].with_user(self.worker)._portal_get_leaves(
            self.employees[2].id,
        )
        self.assertIn(leave.id, [item['id'] for item in payload])
        item = next(item for item in payload if item['id'] == leave.id)
        self.assertFalse(item['can_edit'])
        self.assertFalse(item['can_delete'])

    def test_team_form_creates_normal_leave_instead_of_assignment(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'PORTAL_TEAM_NORMAL_LEAVE',
            'requires_allocation': False,
            'portal_self_service': True,
            'manager_only_requests': False,
        })
        manager_only_type = self.env['hr.leave.type'].create({
            'name': 'PORTAL_TEAM_OLD_ASSIGNMENT_TYPE',
            'requires_allocation': False,
            'portal_self_service': True,
            'manager_only_requests': True,
        })
        HrLeave = self.env['hr.leave'].with_user(self.supervisor)
        employees = HrLeave._portal_get_team_leave_employees()
        worker = next(item for item in employees if item['id'] == self.employees[2].id)
        self.assertIn(leave_type.id, worker['leave_type_ids'])
        leave_types = HrLeave._portal_get_team_leave_types(employees)
        self.assertIn(leave_type.id, [item['id'] for item in leave_types])
        self.assertNotIn(manager_only_type.id, worker['leave_type_ids'])

    def test_portal_dates_use_24_hour_format_without_minutes(self):
        response = self._page(self.worker)
        tree = html.fromstring(response.content)
        card = tree.xpath('//div[contains(@class, "pto-leave-card")][.//*[contains(., "PORTAL_OVERTIME_VISIBLE_TO_OWNER")]]')[0]
        displayed_dates = [text.strip() for text in card.xpath('.//div[contains(@class, "pto-leave-dates")]/span/text()')]
        self.assertEqual(displayed_dates, ['2026-09-10 08', '2026-09-10 16'])
        self.assertTrue(all(':' not in value for value in displayed_dates))
        response = self._page(self.worker, request_category='mission')
        self.assertIn('PORTAL_MISSION_VISIBLE_TO_OWNER', response.text)
        self.assertNotIn('PORTAL_OVERTIME_VISIBLE_TO_OWNER', response.text)
        self.assertNotIn('action="/my/overtime/action"', response.text)
        response = self._page(self.outsider, 'team')
        self.assertNotIn('PORTAL_OVERTIME_VISIBLE_TO_OWNER', response.text)
        self.assertNotIn('action="/my/overtime/create"', response.text)

    def test_supervisor_form_and_employee_cannot_post_approval(self):
        response = self._page(self.supervisor, 'team')
        self.assertIn('action="/my/overtime/create"', response.text)
        self.assertIn('data-bs-toggle="collapse"', response.text)
        self.assertIn('إنشاء عمل إضافي', response.text)
        self.assertIn('PORTAL_OVERTIME_VISIBLE_TO_OWNER', response.text)
        token = html.fromstring(response.content).xpath('//input[@name="csrf_token"]/@value')[0]
        response = self.url_open('/my/overtime/action', data={
            'csrf_token': token, 'overtime_id': self.rec.id, 'action': 'approve'})
        self.assertEqual(response.status_code, 200)
        self.rec.invalidate_recordset()
        self.assertEqual(self.rec.state, 'manager')
        response = self._page(self.worker)
        token = re.search(r'csrf_token: "([^"]+)"', response.text).group(1)
        response = self.url_open('/my/overtime/action', data={
            'csrf_token': token, 'overtime_id': self.rec.id, 'action': 'approve'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('لا يمكنك إدارة هذا الطلب.', response.text)
        self.rec.invalidate_recordset()
        self.assertEqual(self.rec.state, 'manager')
        # CSRF remains required even for denied writes. The shared portal layout
        # includes the token in its session info, while a forged empty token is rejected.
        response = self.url_open('/my/overtime/action', data={'overtime_id': self.rec.id, 'action': 'approve'})
        self.assertEqual(response.status_code, 400)
        self.rec.invalidate_recordset()
        self.assertEqual(self.rec.state, 'manager')

    def test_create_form_submission_with_debug(self):
        response = self._page(self.supervisor, 'team')
        form = html.fromstring(response.content).xpath('//form[contains(@action, "/my/overtime/create")]')[0]
        self.assertEqual(form.get('method').lower(), 'post')
        self.assertNotIn('mission', form.xpath('.//select[@name="kind"]/option/@value'))
        mission_response = self._page(self.supervisor, 'team', request_category='mission')
        self.assertIn('إنشاء مأمورية', mission_response.text)
        mission_form = html.fromstring(mission_response.content).xpath('//form[contains(@action, "/my/overtime/create")]')[0]
        self.assertEqual(mission_form.xpath('.//select[@name="kind"]/option/@value'), ['mission'])
        response = self._page(self.supervisor, 'team')
        form = html.fromstring(response.content).xpath('//form[contains(@action, "/my/overtime/create")]')[0]
        token = form.xpath('.//input[@name="csrf_token"]/@value')[0]
        response = self.url_open(form.get('action') + '?debug=1', data={
            'csrf_token': token, 'employee_id': self.employees[2].id,
            'kind': 'holiday_day', 'date_start': '2026-09-12T08:00',
            'date_stop': '2026-09-12T16:00', 'reason': 'PORTAL_CREATE_DEBUG_TEST',
        })
        self.assertEqual(response.status_code, 200, response.text[:2000])
        created = self.env['thamar.overtime.request'].search([('reason', '=', 'PORTAL_CREATE_DEBUG_TEST')])
        self.assertEqual(len(created), 1)
        self.assertEqual(created.state, 'supervisor')
        self.assertIn('PORTAL_CREATE_DEBUG_TEST', response.text)

    def test_get_creation_url_is_navigation_only(self):
        self._page(self.supervisor, 'team')
        count = self.env['thamar.overtime.request'].search_count([])
        response = self.url_open('/my/overtime/create?debug=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('/my/overtime?scope=team', response.url)
        self.assertEqual(self.env['thamar.overtime.request'].search_count([]), count)
        response = self.url_open('/my/overtime/action?overtime_id=%s&action=approve' % self.rec.id)
        self.assertEqual(response.status_code, 200)
        self.rec.invalidate_recordset()
        self.assertEqual(self.rec.state, 'supervisor')

    def test_invalid_submission_redirects_and_preserves_input(self):
        response = self._page(self.supervisor, 'team')
        token = html.fromstring(response.content).xpath('//input[@name="csrf_token"]/@value')[0]
        count = self.env['thamar.overtime.request'].search_count([])
        response = self.url_open('/my/overtime/create?debug=1', data={
            'csrf_token': token, 'employee_id': self.employees[2].id,
            'kind': 'holiday_day', 'date_start': '2026-09-12T16:00',
            'date_stop': '2026-09-12T08:00', 'reason': 'KEEP_MY_INPUT',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('/my/overtime?scope=team', response.url)
        tree = html.fromstring(response.content)
        self.assertTrue(tree.xpath('//div[@role="alert"]'))
        self.assertEqual(tree.xpath('//textarea[@name="reason"]/text()'), ['KEEP_MY_INPUT'])
        self.assertEqual(tree.xpath('//input[@name="date_start_date"]/@value'), ['2026-09-12'])
        self.assertEqual(tree.xpath('//select[@name="date_start_hour"]/option[@selected]/@value'), ['16'])
        self.assertEqual(self.env['thamar.overtime.request'].search_count([]), count)
        self.assertEqual(self.url_open(response.url).status_code, 200)
