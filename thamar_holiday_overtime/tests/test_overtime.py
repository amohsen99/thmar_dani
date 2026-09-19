from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOvertime(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({'overtime_day_start': 6, 'overtime_day_end': 18,
                           'overtime_holiday_multiplier': 2, 'overtime_policy_confirmed': True})
        cls.company.resource_calendar_id.tz = 'UTC'
        groups = {
            'supervisor': cls.env.ref('thamar_holiday_overtime.group_overtime_manager'),
            'manager': cls.env.ref('thamar_holiday_overtime.group_overtime_manager'),
            'worker': cls.env.ref('thamar_holiday_overtime.group_overtime_user'),
            'outsider': cls.env.ref('thamar_holiday_overtime.group_overtime_user'),
            'hr_admin': cls.env.ref('thamar_holiday_overtime.group_overtime_hr_admin'),
        }
        cls.users = cls.env['res.users'].create([
            {'name': name, 'login': 'ot_test_' + name, 'company_id': cls.company.id,
             'company_ids': [Command.set(cls.company.ids)],
             'group_ids': [Command.set(groups[name].ids)]}
            for name in groups
        ])
        cls.supervisor, cls.manager, cls.worker, cls.outsider, cls.hr_admin = cls.users
        cls.employees = cls.env['hr.employee'].with_context(skip_thamar_leave_policy_checks=True).create([
            {'name': user.name, 'user_id': user.id, 'company_id': cls.company.id,
             'date_version': '2026-01-01', 'contract_date_start': '2026-01-01',
             'wage': 3000, 'resource_calendar_id': cls.company.resource_calendar_id.id}
            for user in cls.users
        ])
        cls.department = cls.env['hr.department'].create({
            'name': 'Overtime Test', 'company_id': cls.company.id,
            'supervisor_id': cls.employees[0].id, 'manager_id': cls.employees[1].id,
        })
        cls.employees[:3].department_id = cls.department
        cls.employee = cls.employees[2]
        cls.model = cls.env['thamar.overtime.request']

    def _request(self, **values):
        vals = {'employee_id': self.employee.id, 'kind': 'hours',
                'date_start': '2026-09-10 17:00:00', 'date_stop': '2026-09-10 20:00:00',
                'reason': 'Test overtime'}
        vals.update(values)
        return self.model.with_user(self.supervisor).sudo().create(vals)

    def _approve(self, rec):
        rec.action_submit()
        rec.action_approve()
        rec.with_user(self.manager).sudo().action_approve()
        rec.with_user(self.hr_admin).sudo().action_hr_approve()
        return rec

    def test_approval_order_and_security(self):
        rec = self._request()
        rec.action_submit()
        with self.assertRaises(AccessError):
            rec.with_user(self.manager).sudo().action_approve()
        with self.assertRaises(AccessError):
            rec.with_user(self.worker).sudo().action_approve()
        with self.assertRaises(AccessError):
            rec.write({'state': 'approved'})
        rec.action_approve()
        self.assertEqual(rec.state, 'manager')
        self.assertFalse(rec.work_entry_ids)
        rec.with_user(self.manager).sudo().action_approve()
        self.assertEqual(rec.state, 'hr')
        self.assertFalse(rec.work_entry_ids)
        with self.assertRaises(AccessError):
            rec.with_user(self.manager).sudo().action_hr_approve()
        rec.with_user(self.hr_admin).sudo().action_hr_approve()
        self.assertEqual(rec.state, 'approved')
        self.assertEqual(len(rec.work_entry_ids), 2)
        self.assertEqual(rec.work_entry_ids.filtered(lambda e: e.overtime_category == 'day').duration, 1)
        self.assertEqual(rec.work_entry_ids.filtered(lambda e: e.overtime_category == 'night').duration, 2)
        with self.assertRaises(AccessError):
            rec.with_user(self.manager).sudo().action_approve()
        with self.assertRaises(UserError):
            rec.write({'reason': 'Tamper'})

    def test_creation_and_record_rules(self):
        vals = {'employee_id': self.employee.id, 'kind': 'hours', 'date_start': '2026-09-11 17:00:00',
                'date_stop': '2026-09-11 18:00:00', 'reason': 'Test'}
        with self.assertRaises(AccessError):
            self.model.with_user(self.worker).sudo().create(vals)
        with self.assertRaises(AccessError):
            self.model.with_user(self.outsider).sudo().create(vals)
        rec = self._request()
        self.assertIn(rec.id, self.model.with_user(self.worker).search([]).ids)
        self.assertNotIn(rec.id, self.model.with_user(self.outsider).search([]).ids)
        self.assertIn(rec.id, self.model.with_user(self.manager).search([]).ids)
        self.assertIn(rec.id, self.model.with_user(self.hr_admin).search([]).ids)
        with self.assertRaises(AccessError):
            self.model.with_user(self.worker).create(vals)
        with self.assertRaises(AccessError):
            self._request(employee_id=self.employees[0].id)

    def test_overlap_and_daily_exclusivity(self):
        self._approve(self._request(kind='holiday_day'))
        rec = self._request(date_start='2026-09-10 21:00:00', date_stop='2026-09-10 22:00:00')
        with self.assertRaises(ValidationError):
            rec.action_submit()

    def test_midnight_and_payroll(self):
        rec = self._approve(self._request(date_start='2026-09-30 23:00:00', date_stop='2026-10-01 02:00:00'))
        self.assertEqual(sorted(rec.work_entry_ids.mapped('duration')), [1, 2])
        slip = self.env['hr.payslip'].new({'employee_id': self.employee.id, 'version_id': self.employee.version_id.id,
            'company_id': self.company.id, 'date_from': '2026-09-01', 'date_to': '2026-09-30'})
        hours_per_day = self.employee.resource_calendar_id.hours_per_day
        self.assertAlmostEqual(slip._get_thamar_overtime_amount('night', 3000), 3000 / 30 / hours_per_day * 1.7)
        self.assertTrue(all(e.work_entry_type_id.amount_rate == 0 for e in rec.work_entry_ids))

    def test_cancel_and_regeneration(self):
        rec = self._approve(self._request())
        entries = rec.work_entry_ids
        entries.with_context(thamar_overtime_generation=True).write({'active': False, 'attendance_id': False})
        self.assertTrue(all(entries.mapped('active')))
        with self.assertRaises(AccessError):
            entries.write({'duration': 4})
        rec.action_cancel()
        self.assertEqual(rec.state, 'cancelled')
        self.assertFalse(any(entries.mapped('active')))

    def test_policy_and_invalid_dates(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._request(date_stop='2026-09-10 16:00:00')
        rec = self._request()
        rec.action_submit()
        rec.action_approve()
        self.company.overtime_policy_confirmed = False
        rec.with_user(self.manager).sudo().action_approve()
        with self.assertRaises(UserError):
            rec.with_user(self.hr_admin).sudo().action_hr_approve()

    def test_backend_manager_create_and_holiday_amount(self):
        rec = self.model.with_user(self.manager).create({
            'employee_id': self.employee.id, 'kind': 'holiday_day',
            'date_start': '2026-09-12 08:00:00', 'date_stop': '2026-09-12 12:00:00',
            'reason': 'Backend creation',
        })
        rec.action_submit()
        rec.with_user(self.supervisor).action_approve()
        rec.action_approve()
        rec.with_user(self.hr_admin).action_hr_approve()
        slip = self.env['hr.payslip'].new({'employee_id': self.employee.id,
            'version_id': self.employee.version_id.id, 'company_id': self.company.id,
            'date_from': '2026-09-01', 'date_to': '2026-09-30'})
        self.assertAlmostEqual(slip._get_thamar_overtime_amount('holiday_day', 3000), 200)
        entries = rec.sudo().work_entry_ids
        self.employee.sudo().generate_work_entries(slip.date_from, slip.date_to, force=True)
        self.assertTrue(all(entries.mapped('active')))
        self.assertEqual(len(rec.sudo().work_entry_ids), 1)

    def test_full_payslip_pays_overtime_once(self):
        self._approve(self._request(kind='holiday_hours'))
        self.employee.generate_work_entries('2026-09-01', '2026-09-30', force=True)
        slip = self.env['hr.payslip'].create({
            'name': 'Overtime payroll integration test',
            'employee_id': self.employee.id, 'version_id': self.employee.version_id.id,
            'company_id': self.company.id, 'struct_id': self.env.ref('hr_payroll.structure_002').id,
            'date_from': '2026-09-01', 'date_to': '2026-09-30',
        })
        slip.compute_sheet()
        basic = sum(slip.line_ids.filtered(lambda line: line.code == 'BASIC').mapped('total'))
        amount = sum(slip.line_ids.filtered(lambda line: line.code == 'TH_OT_HOLIDAY_HOURS').mapped('total'))
        self.assertGreater(basic, 0)
        self.assertAlmostEqual(amount, basic / 30 / self.employee.resource_calendar_id.hours_per_day * 3 * 2)
        self.assertEqual(sum(slip.worked_days_line_ids.filtered(lambda line: line.code == 'TH_OT_HOLIDAY_HOURS').mapped('amount')), 0)
        slip.compute_sheet()
        self.assertEqual(len(slip.line_ids.filtered(lambda line: line.code == 'TH_OT_HOLIDAY_HOURS')), 1)

    def test_mission_pays_first_eight_hours_normally_then_overtime(self):
        rec = self._approve(self._request(
            kind='mission',
            date_start='2026-09-14 08:00:00',
            date_stop='2026-09-14 20:00:00',
            reason='External mission',
        ))
        entries = rec.work_entry_ids
        self.assertEqual(entries.filtered(lambda entry: entry.overtime_category == 'mission_regular').duration, 8)
        self.assertEqual(entries.filtered(lambda entry: entry.overtime_category == 'day').duration, 2)
        self.assertEqual(entries.filtered(lambda entry: entry.overtime_category == 'night').duration, 2)

        slip = self.env['hr.payslip'].new({
            'employee_id': self.employee.id,
            'version_id': self.employee.version_id.id,
            'company_id': self.company.id,
            'date_from': '2026-09-01',
            'date_to': '2026-09-30',
        })
        hourly = 3000 / 30 / self.employee.resource_calendar_id.hours_per_day
        self.assertAlmostEqual(slip._get_thamar_overtime_amount('mission_regular', 3000), 8 * hourly)
        self.assertAlmostEqual(slip._get_thamar_overtime_amount('day', 3000), 2 * hourly * 1.35)
        self.assertAlmostEqual(slip._get_thamar_overtime_amount('night', 3000), 2 * hourly * 1.70)
