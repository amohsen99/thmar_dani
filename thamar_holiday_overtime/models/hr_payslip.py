# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, Command


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.depends('employee_id', 'version_id', 'struct_id', 'date_from', 'date_to')
    def _compute_input_line_ids(self):
        """
        Extend payslip input computation to inject Holiday Overtime
        day/night hours from validated leaves (based on the leave's
        fixed start/end times, NOT work entries).
        """
        super()._compute_input_line_ids()

        hol_ot_day_type = self.env.ref(
            'thamar_holiday_overtime.input_hol_ot_day', raise_if_not_found=False)
        hol_ot_night_type = self.env.ref(
            'thamar_holiday_overtime.input_hol_ot_night', raise_if_not_found=False)

        if not hol_ot_day_type or not hol_ot_night_type:
            return

        overtime_type_ids = (hol_ot_day_type | hol_ot_night_type).ids

        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                continue

            # Remove any existing overtime input lines (avoid duplicates on recompute)
            lines_to_remove = slip.input_line_ids.filtered(
                lambda x: x.input_type_id.id in overtime_type_ids)
            input_line_vals = [Command.unlink(line.id) for line in lines_to_remove]

            # Find validated leaves with split_day_night flag
            # that overlap with the payslip period
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.split_day_night', '=', True),
                ('date_from', '<=', datetime.combine(slip.date_to, time.max)),
                ('date_to', '>=', datetime.combine(slip.date_from, time.min)),
            ])

            if not leaves:
                if lines_to_remove:
                    slip.update({'input_line_ids': input_line_vals})
                continue

            # Get the employee/company timezone
            tz_name = (
                slip.employee_id.resource_calendar_id.tz
                or slip.company_id.resource_calendar_id.tz
                or 'UTC'
            )
            tz = pytz.timezone(tz_name)

            # Split each leave's fixed hours into day/night
            total_day_hours = 0.0
            total_night_hours = 0.0

            for leave in leaves:
                if not leave.date_from or not leave.date_to:
                    continue
                day_start = leave.holiday_status_id.day_start_hour or 6.0
                day_end = leave.holiday_status_id.day_end_hour or 21.0
                day_h, night_h = self._split_leave_hours(
                    leave.date_from, leave.date_to, tz,
                    slip.date_from, slip.date_to,
                    day_start, day_end,
                )
                total_day_hours += day_h
                total_night_hours += night_h

            if total_day_hours > 0:
                input_line_vals.append(Command.create({
                    'name': 'Holiday Overtime - Day',
                    'amount': round(total_day_hours, 2),
                    'input_type_id': hol_ot_day_type.id,
                }))

            if total_night_hours > 0:
                input_line_vals.append(Command.create({
                    'name': 'Holiday Overtime - Night',
                    'amount': round(total_night_hours, 2),
                    'input_type_id': hol_ot_night_type.id,
                }))

            if input_line_vals:
                slip.update({'input_line_ids': input_line_vals})

    @staticmethod
    def _split_leave_hours(leave_start_utc, leave_end_utc, tz,
                           payslip_date_from, payslip_date_to,
                           day_start, day_end):
        """
        Split a leave's fixed start/end times into day and night hours.

        Day hours:   6:00 AM to 9:00 PM
        Night hours: 9:00 PM to 6:00 AM

        Clips to the payslip period and handles multi-day leaves.

        :param leave_start_utc: datetime (UTC naive) from hr.leave.date_from
        :param leave_end_utc: datetime (UTC naive) from hr.leave.date_to
        :param tz: pytz timezone
        :param payslip_date_from: date
        :param payslip_date_to: date
        :return: (day_hours, night_hours)
        """
        # Convert UTC → local timezone
        start_local = pytz.utc.localize(leave_start_utc).astimezone(tz)
        end_local = pytz.utc.localize(leave_end_utc).astimezone(tz)

        # Clip to payslip period
        slip_start = tz.localize(datetime.combine(payslip_date_from, time.min))
        slip_end = tz.localize(datetime.combine(payslip_date_to, time.max))
        start_local = max(start_local, slip_start)
        end_local = min(end_local, slip_end)

        if start_local >= end_local:
            return 0.0, 0.0

        total_day = 0.0
        total_night = 0.0

        # Walk through each calendar day
        current_date = start_local.date()
        last_date = end_local.date()

        while current_date <= last_date:
            day_begin = tz.localize(datetime.combine(current_date, time.min))
            day_end = tz.localize(
                datetime.combine(current_date + timedelta(days=1), time.min))

            # Clip this day's segment to the actual leave period
            seg_start = max(start_local, day_begin)
            seg_end = min(end_local, day_end)

            if seg_start >= seg_end:
                current_date += timedelta(days=1)
                continue

            # Convert to fractional hours within this day
            start_h = (seg_start - day_begin).total_seconds() / 3600.0
            end_h = (seg_end - day_begin).total_seconds() / 3600.0

            # Split against day/night boundaries:
            #   Night 1: [0, 6)    Day: [6, 21)    Night 2: [21, 24)
            for seg_s, seg_e, is_day in [
                (0.0, day_start, False),
                (day_start, day_end, True),
                (day_end, 24.0, False),
            ]:
                overlap = max(0.0, min(end_h, seg_e) - max(start_h, seg_s))
                if is_day:
                    total_day += overlap
                else:
                    total_night += overlap

            current_date += timedelta(days=1)

        return round(total_day, 4), round(total_night, 4)
