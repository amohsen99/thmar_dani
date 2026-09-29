"""Continuous device download and attendance pairing, including overnight shifts."""
import datetime
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BiometricDevice(models.Model):
    _inherit = 'biomteric.device.info'

    auto_sync = fields.Boolean(string='Automatic Attendance Sync', default=True)
    last_auto_sync = fields.Datetime(string='Last Successful Automatic Download', readonly=True, copy=False)
    auto_sync_error = fields.Text(string='Automatic Download Error', readonly=True, copy=False)

    @api.model
    def _lock_attendance_sync(self):
        # One transaction lock shared by manual downloads, manual moves and
        # both scheduled actions. PostgreSQL releases it even if the job fails.
        self.env.cr.execute('SELECT pg_try_advisory_xact_lock(%s, %s)', (903719, 1))
        return self.env.cr.fetchone()[0]

    @api.model
    def _cron_download_attendance(self):
        if not self._lock_attendance_sync():
            return
        for device in self.search([('auto_sync', '=', True)], order='id'):
            # Overlap each successful fetch to catch delayed device logs. After
            # an outage, resume from the last success rather than from today.
            until = fields.Datetime.now()
            since = (device.last_auto_sync - datetime.timedelta(days=2)
                     if device.last_auto_sync else datetime.datetime(1950, 1, 1))
            try:
                with self.env.cr.savepoint():
                    device.with_context(zk_sync_from=since, zk_sync_to=until).download_attendance_oldapi()
                    device.write({'last_auto_sync': until, 'auto_sync_error': False})
            except Exception as error:
                _logger.exception('Automatic attendance download failed for device %s', device.id)
                device.auto_sync_error = str(error)


class DraftAttendance(models.Model):
    _inherit = 'hr.draft.attendance'

    @api.model
    def _cron_move_attendance(self):
        devices_model = self.env['biomteric.device.info']
        if not devices_model._lock_attendance_sync():
            return
        # Drafts may come from manual downloads as well as scheduled ones.
        # An unavailable or never-synced device must not block the whole queue.
        # Late arrivals still pass the chronological safety checks below.
        cutoff = fields.Datetime.now() - datetime.timedelta(minutes=2)
        drafts = self.search([
            ('moved', '=', False), ('employee_id', '!=', False),
            ('attendance_status', 'in', ['sign_in', 'sign_out']),
            ('name', '<=', cutoff),
        ], order='name, id', limit=1000)
        for employee, punches in drafts.grouped('employee_id').items():
            try:
                with self.env.cr.savepoint():
                    self._move_employee_punches(punches)
            except Exception:
                # Roll back all punches for this employee; other employees can
                # still proceed and these drafts remain available for retry.
                _logger.exception('Automatic attendance move failed for employee %s', employee.id)

    def _move_employee_punches(self, punches):
        """Pair one chronological employee batch using the manual wizard rules."""
        if not punches:
            return
        employee = punches.employee_id
        employee.ensure_one()
        wizard = self.env['move.draft.attendance.wizard']
        mode, max_shift_hours, anti_dup_minutes = wizard._get_config()
        processor = {
            'sequence': wizard._process_sequence_mode,
            'device_type': wizard._process_device_type_mode,
            'forced_device': wizard._process_forced_device_mode,
        }[mode]
        attendance_model = self.env['hr.attendance'].with_context(skip_work_entries=True)
        open_attendance = attendance_model.search([
            ('employee_id', '=', employee.id), ('check_out', '=', False),
        ], order='check_in desc', limit=1)
        previous = self.search([
            ('employee_id', '=', employee.id), ('moved', '=', True),
            ('moved_to', '!=', False),
        ], order='name desc, id desc', limit=1)
        if previous and punches[0].name < previous.name:
            raise UserError(_('Late punches precede already moved attendance; review these drafts manually.'))
        if open_attendance and open_attendance.check_in > punches[0].name:
            raise UserError(_('An open attendance starts after these punches; review these drafts manually.'))
        last_punch_time = previous.name if previous else None
        delta = datetime.timedelta(minutes=max(0, anti_dup_minutes))
        existing = attendance_model.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', punches[0].name),
            ('check_in', '<=', punches[-1].name),
        ])
        existing_set = {(employee.id, str(att.check_in)): att for att in existing}
        for punch in punches:
            if last_punch_time and punch.name - last_punch_time < delta:
                punch.write({'moved': True})
                continue
            marks, creates, open_attendance, skipped = processor(
                punch, open_attendance, employee.id, employee.name,
                max_shift_hours, existing_set, attendance_model)
            for draft, attendance_id in marks:
                draft.write({'moved': True, 'moved_to': attendance_id})
            last_punch_time = punch.name
