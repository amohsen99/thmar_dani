from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

from ..models import biometric_device


@tagged('post_install', '-at_install')
class TestAttendanceCron(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Continuous shift test', 'global_attendance_id': 'cron-test-100',
        })
        cls.device = cls.env['biomteric.device.info'].create({
            'name': 'Cron device', 'ipaddress': '192.0.2.100',
            'time_zone': 'Asia/Riyadh', 'force_action': 'sign_in',
        })
        cls.drafts = cls.env['hr.draft.attendance']
        cls.env['ir.config_parameter'].sudo().set_param(
            'hr_attendance_zktecho.attendance_anti_duplicate_minutes', '5')

    def punch(self, time, status):
        return self.drafts.create({
            'employee_id': self.employee.id, 'name': time,
            'attendance_status': status, 'device_id': self.device.id,
        })

    def test_three_shifts_across_separate_runs(self):
        for mode in ('sequence', 'device_type', 'forced_device'):
            with self.subTest(mode=mode):
                self.env['ir.config_parameter'].sudo().set_param(
                    'hr_attendance_zktecho.attendance_routing_mode', mode)
                for start, end in (
                    ('2026-09-01 06:00:00', '2026-09-01 14:00:00'),
                    ('2026-09-01 14:10:00', '2026-09-01 22:00:00'),
                    ('2026-09-01 22:10:00', '2026-09-02 06:00:00'),
                ):
                    check_in = self.punch(start, 'sign_in')
                    self.drafts._move_employee_punches(check_in)
                    attendance = check_in.moved_to
                    self.assertFalse(attendance.check_out)
                    check_out = self.punch(end, 'sign_out')
                    self.drafts._move_employee_punches(check_out)
                    self.assertEqual(check_out.moved_to, attendance)
                    self.assertEqual(attendance.check_out, fields.Datetime.to_datetime(end))
                    self.assertFalse(attendance.is_missing)
                self.drafts.search([('employee_id', '=', self.employee.id)]).unlink()
                self.env['hr.attendance'].search([('employee_id', '=', self.employee.id)]).unlink()

    def test_duplicate_across_runs_keeps_check_in_open(self):
        first = self.punch('2026-09-01 22:00:00', 'sign_in')
        self.drafts._move_employee_punches(first)
        duplicate = self.punch('2026-09-01 22:02:00', 'sign_in')
        self.drafts._move_employee_punches(duplicate)
        self.assertTrue(duplicate.moved)
        self.assertFalse(duplicate.moved_to)
        self.assertFalse(first.moved_to.check_out)

    def test_late_punch_requires_review(self):
        first = self.punch('2026-09-01 22:00:00', 'sign_in')
        self.drafts._move_employee_punches(first)
        late = self.punch('2026-09-01 20:00:00', 'sign_in')
        with self.assertRaises(UserError):
            self.drafts._move_employee_punches(late)
        self.assertFalse(late.moved)
        self.assertFalse(first.moved_to.check_out)

    def test_download_utc_window_sorted_and_idempotent_without_disabling_device(self):
        connection = MagicMock()
        connection.get_attendance.return_value = [
            SimpleNamespace(timestamp=datetime(2026, 9, 2, 2), user_id='cron-test-100'),
            SimpleNamespace(timestamp=datetime(2026, 9, 2, 1), user_id='cron-test-100'),
            SimpleNamespace(timestamp=datetime(2026, 9, 2, 0), user_id='cron-test-100'),
        ]
        device = self.device.with_context(
            zk_sync_from=datetime(2026, 9, 1, 22),
            zk_sync_to=datetime(2026, 9, 1, 23))
        with patch.object(biometric_device, 'ZK') as zk:
            zk.return_value.connect.return_value = connection
            device.download_attendance_oldapi()
            device.download_attendance_oldapi()
        punches = self.drafts.search([('employee_id', '=', self.employee.id)], order='name')
        self.assertEqual(punches.mapped('name'), [datetime(2026, 9, 1, 22), datetime(2026, 9, 1, 23)])
        connection.disable_device.assert_not_called()
        connection.clear_attendance.assert_not_called()
        self.assertEqual(connection.disconnect.call_count, 2)

    def test_move_waits_for_download_and_does_not_repeat(self):
        punch = self.punch('2026-09-01 22:00:00', 'sign_in')
        with patch.object(type(self.device), 'search', return_value=self.device):
            self.drafts._cron_move_attendance()
            self.assertFalse(punch.moved)
            self.device.last_auto_sync = datetime(2026, 9, 1, 22, 1)
            self.drafts._cron_move_attendance()
            self.assertFalse(punch.moved)
            self.device.last_auto_sync = datetime(2026, 9, 1, 22, 5)
            self.drafts._cron_move_attendance()
            self.assertTrue(punch.moved)
            self.drafts._cron_move_attendance()
        self.assertEqual(self.env['hr.attendance'].search_count([('employee_id', '=', self.employee.id)]), 1)

    def test_download_failure_preserves_watermark_and_other_device_succeeds(self):
        second = self.device.copy({'ipaddress': '192.0.2.101'})
        before = datetime(2026, 9, 1)
        self.device.last_auto_sync = before
        devices = self.device | second
        def download(device):
            if device.id == self.device.id:
                raise UserError('Device offline')
            return True
        with patch.object(type(self.device), 'search', return_value=devices), \
             patch.object(type(self.device), 'download_attendance_oldapi', autospec=True, side_effect=download):
            self.device._cron_download_attendance()
        self.assertEqual(self.device.last_auto_sync, before)
        self.assertIn('Device offline', self.device.auto_sync_error)
        self.assertTrue(second.last_auto_sync)

    def test_shared_lock_prevents_overlapping_transactions(self):
        self.assertTrue(self.device._lock_attendance_sync())
        with self.env.registry.cursor() as cr:
            cr.execute('SELECT pg_try_advisory_xact_lock(%s, %s)', (903719, 1))
            self.assertFalse(cr.fetchone()[0])

    def test_slowest_device_limits_move_cutoff(self):
        second = self.device.copy({'ipaddress': '192.0.2.102'})
        self.device.last_auto_sync = datetime(2026, 9, 2, 10)
        second.last_auto_sync = datetime(2026, 9, 1, 21)
        punch = self.punch('2026-09-01 22:00:00', 'sign_in')
        with patch.object(type(self.device), 'search', return_value=self.device | second):
            self.drafts._cron_move_attendance()
            self.assertFalse(punch.moved)
            second.last_auto_sync = datetime(2026, 9, 2, 10)
            self.drafts._cron_move_attendance()
            self.assertTrue(punch.moved)

    def test_employee_failure_rolls_back_only_that_employee(self):
        other = self.env['hr.employee'].create({'name': 'Other shift employee', 'global_attendance_id': 'cron-test-101'})
        failed = self.punch('2026-09-01 22:00:00', 'sign_in')
        successful = failed.copy({'employee_id': other.id})
        self.device.last_auto_sync = datetime(2026, 9, 2, 10)
        original = type(self.drafts)._move_employee_punches
        def move(model, punches):
            original(model, punches)
            if punches.employee_id == self.employee:
                raise UserError('Injected processing failure')
        with patch.object(type(self.device), 'search', return_value=self.device), \
             patch.object(type(self.drafts), '_move_employee_punches', autospec=True, side_effect=move):
            self.drafts._cron_move_attendance()
        self.assertFalse(failed.moved)
        self.assertTrue(successful.moved)
        self.assertFalse(self.env['hr.attendance'].search([('employee_id', '=', self.employee.id)]))
