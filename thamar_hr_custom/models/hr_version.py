# -*- coding: utf-8 -*-
"""Thamar HR Version overrides.

Provides a direct attendance-to-work-entry generation method that bypasses
Odoo's calendar-based pipeline.  This avoids the date_generated_from/to
watermark bug that silently skips new attendance records.

Also patches the singleton crash in _get_attendance_intervals where
overtime.status is accessed on a multi-record recordset.
"""
import logging
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrVersion(models.Model):
    _inherit = 'hr.version'

    # ------------------------------------------------------------------
    # Fix: patch the enterprise _get_attendance_intervals to handle
    # multi-record overtime recordsets safely (singleton crash on line 94
    # of the enterprise hr_work_entry_attendance module).
    # ------------------------------------------------------------------
    def _get_attendance_intervals(self, start_dt, end_dt):
        """Override to fix singleton crash on overtime.status.

        The enterprise ``hr_work_entry_attendance`` module accesses
        ``overtime.status`` on a potentially multi-record recordset
        (Intervals can merge overlapping entries, producing a stacked
        third element).  We replicate the attendance + overtime logic
        but iterate over each overtime record safely.
        """
        from collections import defaultdict as _defaultdict
        from pytz import timezone as _timezone
        from odoo.tools.intervals import Intervals as _Intervals
        from datetime import timedelta as _timedelta

        start_naive = start_dt.replace(tzinfo=None)
        end_naive = end_dt.replace(tzinfo=None)

        # ── Attendance-based intervals (same as enterprise) ──
        att_versions = self.filtered(
            lambda c: c.work_entry_source == 'attendance')
        search_domain = [
            ('employee_id', 'in', att_versions.employee_id.ids),
            ('check_in', '<', end_naive),
            ('check_out', '>', start_naive),
        ]
        resource_ids = att_versions.employee_id.resource_id.ids
        attendances = (
            self.env['hr.attendance'].sudo().search(search_domain)
            if att_versions else self.env['hr.attendance']
        )
        intervals = _defaultdict(list)
        for attendance in attendances:
            emp_cal = attendance._get_employee_calendar()
            resource = attendance.employee_id.resource_id
            tz = _timezone(emp_cal.tz or resource.tz)
            check_in_tz = attendance.check_in.astimezone(tz)
            check_out_tz = attendance.check_out.astimezone(tz)
            if attendance.overtime_status == 'refused':
                check_out_tz -= _timedelta(
                    hours=attendance.validated_overtime_hours)
            if (attendance.employee_id.resource_calendar_id
                    and not attendance.employee_id.resource_calendar_id.flexible_hours):
                lunch_intervals = (
                    attendance.employee_id._employee_attendance_intervals(
                        check_in_tz, check_out_tz, lunch=True))
                leaves = (
                    emp_cal._leave_intervals_batch(
                        check_in_tz, check_out_tz, None)[False]
                    if emp_cal
                    else _Intervals([], keep_distinct=True)
                )
                real_lunch = lunch_intervals - leaves
                att_intervals = (
                    _Intervals([(check_in_tz, check_out_tz, attendance)])
                    - real_lunch
                )
            else:
                att_intervals = _Intervals(
                    [(check_in_tz, check_out_tz, attendance)])
            for interval in att_intervals:
                intervals[resource.id].append((
                    max(start_dt, interval[0]),
                    min(end_dt, interval[1]),
                    attendance,
                ))

        mapped_intervals = {
            r: _Intervals(intervals[r], keep_distinct=True)
            for r in resource_ids
        }

        # Call the BASE (calendar) _get_attendance_intervals,
        # skipping the enterprise override we are replacing.
        from odoo.addons.hr_work_entry_attendance.models.hr_version import (
            HrVersion as _EnterpriseHrVersion,
        )
        base_result = super(
            _EnterpriseHrVersion, self
        )._get_attendance_intervals(start_dt, end_dt)
        mapped_intervals.update(base_result)

        # ── Overtime intervals ──
        overtime_intervals = {
            r: _Intervals(keep_distinct=True) for r in mapped_intervals
        }
        overtime_versions = self.filtered(
            lambda c: c.work_entry_source == 'attendance'
            or c.overtime_from_attendance)
        overtime_intervals.update(
            overtime_versions._get_overtime_intervals(start_dt, end_dt))

        # ── FIX: handle multi-record overtime recordsets safely ──
        work_entry_overtime_intervals = _defaultdict(list)
        for r, itvs in overtime_intervals.items():
            for start, end, overtime in itvs:
                has_wet = bool(overtime.rule_ids.work_entry_type_id)
                all_approved = all(
                    ot.status == 'approved' for ot in overtime)
                if not (has_wet and all_approved):
                    continue
                work_entry_overtime_intervals[r].append(
                    (start, end, overtime))

        return {
            r: (mapped_intervals[r] - overtime_intervals[r])
            | _Intervals(
                work_entry_overtime_intervals[r], keep_distinct=True)
            for r in mapped_intervals
        }

    # ------------------------------------------------------------------
    # Direct attendance → work entry generation
    # ------------------------------------------------------------------

    def generate_attendance_work_entries(self, date_from, date_to):
        """Create work entries directly from hr.attendance records.

        This method is designed for attendance-based employees.  Instead
        of using Odoo's calendar-based pipeline (which has watermark bugs
        that skip new attendances), it:

        1. Queries hr.attendance records in the date range
        2. Groups them by (employee, date) in the employee's timezone
        3. Sums worked hours per day
        4. Deletes existing non-validated work entries for those days
        5. Creates one hr.work.entry per day per employee

        This is idempotent: safe to re-run without duplicates.

        :param date_from: date or datetime
        :param date_to:   date or datetime
        :return: created hr.work.entry recordset
        """
        if isinstance(date_from, datetime):
            date_from = date_from.date()
        if isinstance(date_to, datetime):
            date_to = date_to.date()

        # Filter to attendance-based versions only
        att_versions = self.filtered(
            lambda v: v.work_entry_source == 'attendance')
        if not att_versions:
            return self.env['hr.work.entry']

        # Resolve the attendance work entry type
        att_work_entry_type = self.env.ref(
            'hr_work_entry.work_entry_type_attendance',
            raise_if_not_found=False)
        if not att_work_entry_type:
            _logger.error('Missing work entry type: hr_work_entry.work_entry_type_attendance')
            return self.env['hr.work.entry']

        # 1. Fetch all attendances in date range for these employees
        employee_ids = att_versions.mapped('employee_id').ids
        start_naive = datetime.combine(date_from, time.min)
        end_naive = datetime.combine(date_to, time.max)

        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', 'in', employee_ids),
            ('check_in', '<=', end_naive),
            ('check_out', '>', start_naive),
            ('check_out', '!=', False),
        ])

        if not attendances:
            _logger.info(
                'No attendances found for %d employees in %s → %s',
                len(employee_ids), date_from, date_to)
            return self.env['hr.work.entry']

        # Build a map: version_id -> version for each employee
        version_by_emp = {}
        for version in att_versions:
            version_by_emp[version.employee_id.id] = version

        # 2. Group attendance hours by (employee_id, local_date)
        #    Key: (employee_id, date) → total_hours
        daily_hours = defaultdict(float)
        daily_names = {}  # (emp_id, date) → name for the work entry

        for att in attendances:
            emp = att.employee_id
            version = version_by_emp.get(emp.id)
            if not version:
                continue

            # Resolve timezone
            tz_name = (
                version.resource_calendar_id.tz
                or emp.resource_calendar_id.tz
                or emp.company_id.resource_calendar_id.tz
                or 'UTC'
            )
            tz = pytz.timezone(tz_name)

            # Convert to local timezone
            check_in_utc = pytz.utc.localize(att.check_in) if not att.check_in.tzinfo else att.check_in
            check_out_utc = pytz.utc.localize(att.check_out) if not att.check_out.tzinfo else att.check_out

            check_in_local = check_in_utc.astimezone(tz)
            check_out_local = check_out_utc.astimezone(tz)

            # Clip to the requested date range
            range_start = tz.localize(datetime.combine(date_from, time.min))
            range_end = tz.localize(datetime.combine(date_to, time.max))
            check_in_local = max(check_in_local, range_start)
            check_out_local = min(check_out_local, range_end)

            if check_in_local >= check_out_local:
                continue

            # Split across midnight if needed
            current = check_in_local
            while current < check_out_local:
                next_midnight = tz.localize(
                    datetime.combine(current.date() + timedelta(days=1), time.min))
                segment_end = min(check_out_local, next_midnight)

                hours = (segment_end - current).total_seconds() / 3600.0
                local_date = current.date()

                key = (emp.id, local_date)
                daily_hours[key] += hours
                daily_names[key] = "%s: %s" % (att_work_entry_type.name, emp.name)

                current = segment_end

        if not daily_hours:
            return self.env['hr.work.entry']

        # 3. Delete existing non-validated work entries for these days
        #    to avoid duplicates (idempotent)
        all_dates = set()
        all_emp_ids = set()
        for (emp_id, dt) in daily_hours:
            all_dates.add(dt)
            all_emp_ids.add(emp_id)

        min_date = min(all_dates)
        max_date = max(all_dates)

        existing_entries = self.env['hr.work.entry'].sudo().search([
            ('employee_id', 'in', list(all_emp_ids)),
            ('date', '>=', min_date),
            ('date', '<=', max_date),
            ('state', '!=', 'validated'),
            ('work_entry_type_id', '=', att_work_entry_type.id),
        ])

        # Only delete entries for days we're about to recreate
        entries_to_delete = existing_entries.filtered(
            lambda e: (e.employee_id.id, e.date) in daily_hours)

        if entries_to_delete:
            _logger.info(
                'Deleting %d existing work entries before recreation',
                len(entries_to_delete))
            entries_to_delete.with_context(hr_work_entry_no_check=True).unlink()

        # 4. Create new work entries
        vals_list = []
        for (emp_id, local_date), hours in daily_hours.items():
            version = version_by_emp.get(emp_id)
            if not version:
                continue

            # Clamp hours to valid range
            if hours <= 0:
                continue
            if hours > 24:
                _logger.warning(
                    'Employee %s on %s has %.2f hours, clamping to 24',
                    emp_id, local_date, hours)
                hours = 24.0

            vals_list.append({
                'name': daily_names.get((emp_id, local_date), att_work_entry_type.name),
                'employee_id': emp_id,
                'version_id': version.id,
                'company_id': version.company_id.id,
                'work_entry_type_id': att_work_entry_type.id,
                'date': local_date,
                'duration': round(hours, 4),
                'state': 'draft',
            })

        if not vals_list:
            return self.env['hr.work.entry']

        _logger.info(
            'Creating %d attendance work entries for %d employees (%s → %s)',
            len(vals_list), len(all_emp_ids), date_from, date_to)

        new_entries = self.env['hr.work.entry'].with_context(
            hr_work_entry_no_check=True,
            tracking_disable=True,
        ).create(vals_list)

        # Update the generation watermarks so the cron doesn't re-trigger
        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)
        for version in att_versions:
            if version.date_generated_from > start_dt:
                version.date_generated_from = start_dt
            if version.date_generated_to < end_dt:
                version.date_generated_to = end_dt
            version.last_generation_date = fields.Date.today()

        return new_entries
