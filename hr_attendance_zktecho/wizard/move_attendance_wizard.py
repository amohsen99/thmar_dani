import logging
import datetime
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger('move_attendance')

BATCH_SIZE = 500


class move_attendance_wizard(models.TransientModel):
    _name = "move.draft.attendance.wizard"
    _description = 'Move Draft Attendance Wizard'

    def _default_date1(self):
        return fields.Datetime.now().replace(day=1, hour=0, minute=0, second=0)

    def _default_date2(self):
        today = fields.Datetime.now()
        if today.month == 12:
            last_day = today.replace(year=today.year+1, month=1, day=1) - datetime.timedelta(days=1)
        else:
            last_day = today.replace(month=today.month+1, day=1) - datetime.timedelta(days=1)
        return last_day.replace(hour=23, minute=59, second=59)

    date1 = fields.Datetime('From', required=True, default=_default_date1)
    date2 = fields.Datetime('To', required=True, default=_default_date2)
    employee_ids = fields.Many2many('hr.employee', 'move_att_employee_rel', 'employee_id', 'wiz_id')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_config(self):
        """Read all routing configuration from ir.config_parameter."""
        ICP = self.env['ir.config_parameter'].sudo()
        routing_mode = ICP.get_param(
            'hr_attendance_zktecho.attendance_routing_mode', 'sequence')
        max_shift_hours = int(
            ICP.get_param('hr_attendance_zktecho.attendance_max_shift_hours', '20'))
        anti_dup_minutes = int(
            ICP.get_param('hr_attendance_zktecho.attendance_anti_duplicate_minutes', '5'))
        return routing_mode, max_shift_hours, anti_dup_minutes

    def _is_within_shift(self, open_attendance, punch_time, max_shift_hours):
        """Return True if *punch_time* falls within *max_shift_hours* of the
        open attendance's check_in.  The punch must be AFTER check_in."""
        if not open_attendance or not open_attendance.check_in:
            return False
        delta = punch_time - open_attendance.check_in
        return datetime.timedelta(0) <= delta <= datetime.timedelta(hours=max_shift_hours)

    def _auto_close_stale(self, open_attendance, emp_name, max_shift_hours,
                          punch_time):
        """If the open attendance is older than max_shift_hours, close it and
        return None. Otherwise return the attendance unchanged."""
        if not open_attendance or open_attendance.check_out:
            return None
        if not self._is_within_shift(open_attendance, punch_time,
                                     max_shift_hours):
            open_attendance.write({
                'check_out': open_attendance.check_in,
                'is_missing': True,
            })
            _logger.warning(
                'Auto-closed stale attendance for %s (check_in: %s, '
                'exceeded %dh shift limit)',
                emp_name, open_attendance.check_in, max_shift_hours)
            return None
        return open_attendance

    # ------------------------------------------------------------------
    # Per-mode processors
    # ------------------------------------------------------------------

    def _process_sequence_mode(self, line, open_attendance, emp_id, emp_name,
                               max_shift_hours, existing_set, HrAttendance):
        """Mode 'sequence': alternate In/Out ignoring device punch type."""
        punch_time = line.name
        drafts_to_mark = []
        creates = 0

        # Auto-close stale open attendance
        open_attendance = self._auto_close_stale(
            open_attendance, emp_name, max_shift_hours, punch_time)

        if open_attendance and not open_attendance.check_out:
            # Close it (check-out) — guard against check_out < check_in
            if punch_time >= open_attendance.check_in:
                open_attendance.write({'check_out': punch_time})
                drafts_to_mark.append((line, open_attendance.id))
                open_attendance = None  # now closed
            else:
                # Punch is before open attendance's check_in → auto-close
                # the stale open attendance and treat this as a new check-in
                open_attendance.write({
                    'check_out': open_attendance.check_in,
                    'is_missing': True,
                })
                _logger.warning(
                    'sequence: punch %s is before open check_in %s for %s, '
                    'auto-closed stale and creating new check-in',
                    punch_time, open_attendance.check_in, emp_name)
                new_att = HrAttendance.create({
                    'employee_id': emp_id,
                    'check_in': punch_time,
                })
                drafts_to_mark.append((line, new_att.id))
                dup_key = (emp_id, str(punch_time))
                existing_set[dup_key] = new_att
                open_attendance = new_att
                creates += 1
        else:
            # Check duplicate
            dup_key = (emp_id, str(punch_time))
            existing = existing_set.get(dup_key)
            if existing:
                drafts_to_mark.append((line, existing.id))
                open_attendance = existing if not existing.check_out else None
                return drafts_to_mark, creates, open_attendance, True  # skipped

            # Create new check-in
            new_att = HrAttendance.create({
                'employee_id': emp_id,
                'check_in': punch_time,
            })
            drafts_to_mark.append((line, new_att.id))
            existing_set[dup_key] = new_att
            open_attendance = new_att
            creates += 1

        return drafts_to_mark, creates, open_attendance, False

    def _process_device_type_mode(self, line, open_attendance, emp_id,
                                  emp_name, max_shift_hours, existing_set,
                                  HrAttendance):
        """Mode 'device_type': respect sign_in/sign_out from draft record,
        with max_shift_hours safety."""
        punch_time = line.name
        status = line.attendance_status
        drafts_to_mark = []
        creates = 0

        # Auto-close stale open attendance
        open_attendance = self._auto_close_stale(
            open_attendance, emp_name, max_shift_hours, punch_time)

        if status == 'sign_in':
            dup_key = (emp_id, str(punch_time))
            existing = existing_set.get(dup_key)
            if existing:
                drafts_to_mark.append((line, existing.id))
                open_attendance = existing if not existing.check_out else open_attendance
                return drafts_to_mark, creates, open_attendance, True

            # Auto-close orphaned open if still present
            if open_attendance and not open_attendance.check_out:
                open_attendance.write({
                    'check_out': open_attendance.check_in,
                    'is_missing': True,
                })
                _logger.warning(
                    'Auto-closed orphaned attendance for %s (check_in: %s)',
                    emp_name, open_attendance.check_in)

            new_att = HrAttendance.create({
                'employee_id': emp_id,
                'check_in': punch_time,
            })
            drafts_to_mark.append((line, new_att.id))
            existing_set[dup_key] = new_att
            open_attendance = new_att
            creates += 1

        elif status == 'sign_out':
            if open_attendance and not open_attendance.check_out \
                    and punch_time >= open_attendance.check_in:
                open_attendance.write({'check_out': punch_time})
                drafts_to_mark.append((line, open_attendance.id))
                open_attendance = None  # closed
            else:
                # Orphaned sign_out → placeholder
                new_att = HrAttendance.create({
                    'employee_id': emp_id,
                    'check_in': punch_time,
                    'check_out': punch_time,
                    'is_missing': True,
                })
                drafts_to_mark.append((line, new_att.id))
                open_attendance = None
                creates += 1
                _logger.warning(
                    'Orphaned sign_out for %s at %s', emp_name, punch_time)
        else:
            # sign_none – skip
            return drafts_to_mark, creates, open_attendance, True

        return drafts_to_mark, creates, open_attendance, False

    def _process_forced_device_mode(self, line, open_attendance, emp_id,
                                    emp_name, max_shift_hours, existing_set,
                                    HrAttendance):
        """Mode 'forced_device': use the attendance_status captured at sync
        time.  This avoids the race condition where changing a device's
        force_action *after* sync would corrupt historical data."""
        punch_time = line.name
        drafts_to_mark = []
        creates = 0

        # Read the status that was captured at sync time (Stage 1),
        # NOT the current device.force_action which may have changed.
        status = line.attendance_status
        if not status or status == 'sign_none':
            # No usable status captured → fall back to sequence mode
            _logger.warning(
                'forced_device mode: draft %s has no attendance_status, '
                'falling back to sequence for %s', line.id, emp_name)
            return self._process_sequence_mode(
                line, open_attendance, emp_id, emp_name, max_shift_hours,
                existing_set, HrAttendance)

        # Auto-close stale open attendance
        open_attendance = self._auto_close_stale(
            open_attendance, emp_name, max_shift_hours, punch_time)

        if status == 'sign_in':
            dup_key = (emp_id, str(punch_time))
            existing = existing_set.get(dup_key)
            if existing:
                drafts_to_mark.append((line, existing.id))
                open_attendance = existing if not existing.check_out else open_attendance
                return drafts_to_mark, creates, open_attendance, True

            # If there's still an open attendance (within shift), auto-close
            if open_attendance and not open_attendance.check_out:
                open_attendance.write({
                    'check_out': open_attendance.check_in,
                    'is_missing': True,
                })
                _logger.warning(
                    'forced_device sign_in: auto-closed open attendance for %s',
                    emp_name)

            new_att = HrAttendance.create({
                'employee_id': emp_id,
                'check_in': punch_time,
            })
            drafts_to_mark.append((line, new_att.id))
            existing_set[dup_key] = new_att
            open_attendance = new_att
            creates += 1

        elif status == 'sign_out':
            if open_attendance and not open_attendance.check_out \
                    and punch_time >= open_attendance.check_in:
                open_attendance.write({'check_out': punch_time})
                drafts_to_mark.append((line, open_attendance.id))
                open_attendance = None
            else:
                # No open record → placeholder
                new_att = HrAttendance.create({
                    'employee_id': emp_id,
                    'check_in': punch_time,
                    'check_out': punch_time,
                    'is_missing': True,
                })
                drafts_to_mark.append((line, new_att.id))
                open_attendance = None
                creates += 1
                _logger.warning(
                    'forced_device sign_out: no open attendance for %s at %s, '
                    'created placeholder', emp_name, punch_time)

        return drafts_to_mark, creates, open_attendance, False

    # ------------------------------------------------------------------
    # Main action
    # ------------------------------------------------------------------

    def move_confirm(self):
        HrAttendance = self.env['hr.attendance'].with_context(skip_work_entries=True)
        DraftAttendance = self.env['hr.draft.attendance']

        routing_mode, max_shift_hours, anti_dup_minutes = self._get_config()
        anti_dup_delta = datetime.timedelta(minutes=anti_dup_minutes)

        _logger.info(
            'Move wizard started: mode=%s, max_shift=%dh, anti_dup=%dmin',
            routing_mode, max_shift_hours, anti_dup_minutes)

        # ──────────────────────────────────────────────────────────────
        # 1. BULK FETCH: all draft records in ONE query
        # ──────────────────────────────────────────────────────────────
        draft_domain = [
            ('attendance_status', '!=', 'sign_none'),
            ('name', '>=', self.date1),
            ('name', '<=', self.date2),
            ('moved', '=', False),
        ]
        if self.employee_ids:
            draft_domain.append(('employee_id', 'in', self.employee_ids.ids))

        all_drafts = DraftAttendance.search(draft_domain, order='name asc')

        if not all_drafts:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Move Complete'),
                    'message': _('No draft attendance records to move.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # ──────────────────────────────────────────────────────────────
        # PRE-MATERIALIZE: read all draft data into plain Python dicts
        # so nothing depends on ORM cache after cr.commit().
        # ──────────────────────────────────────────────────────────────
        draft_data_list = []
        for draft in all_drafts:
            draft_data_list.append({
                'id': draft.id,
                'name': draft.name,
                'employee_id': draft.employee_id.id,
                'attendance_status': draft.attendance_status,
                'device_id': draft.device_id.id if draft.device_id else False,
            })

        # Group drafts by employee_id, preserving chronological order
        drafts_by_emp = defaultdict(list)
        emp_ids_in_scope = set()
        for dd in draft_data_list:
            drafts_by_emp[dd['employee_id']].append(dd)
            emp_ids_in_scope.add(dd['employee_id'])

        emp_ids_list = list(emp_ids_in_scope)

        # ──────────────────────────────────────────────────────────────
        # 2. BULK FETCH: existing open attendances (no check_out)
        #    Materialize to IDs for re-browsing in fresh cursors.
        # ──────────────────────────────────────────────────────────────
        open_attendances_recs = HrAttendance.search([
            ('employee_id', 'in', emp_ids_list),
            ('check_out', '=', False),
        ], order='check_in desc')

        open_att_id_map = {}
        for att in open_attendances_recs:
            if att.employee_id.id not in open_att_id_map:
                open_att_id_map[att.employee_id.id] = att.id

        # ──────────────────────────────────────────────────────────────
        # 3. BULK FETCH: existing hr.attendance in date range (IDs only)
        # ──────────────────────────────────────────────────────────────
        existing_attendances = HrAttendance.search([
            ('employee_id', 'in', emp_ids_list),
            ('check_in', '>=', self.date1),
            ('check_in', '<=', self.date2),
        ])

        existing_id_set = {}
        for att in existing_attendances:
            key = (att.employee_id.id, str(att.check_in))
            existing_id_set[key] = att.id

        # Pre-cache employee names
        emp_name_map = {}
        if emp_ids_list:
            for emp in self.env['hr.employee'].browse(emp_ids_list):
                emp_name_map[emp.id] = emp.name

        # ──────────────────────────────────────────────────────────────
        # 4. PROCESS: iterate by employee, use fresh cursor per employee
        #    to avoid "cursor already closed" caused by ORM recompute
        #    cascades (hr.attendance overtime fields) during flush/commit.
        # ──────────────────────────────────────────────────────────────
        error_lines = []
        moved_count = 0
        skipped_count = 0
        dedup_skipped = 0

        for emp_idx, emp_id in enumerate(emp_ids_list):
            emp_name = emp_name_map.get(emp_id, str(emp_id))
            emp_drafts = drafts_by_emp[emp_id]

            try:
                new_cr = self.env.registry.cursor()
                try:
                    new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                    new_HrAttendance = new_env['hr.attendance'].with_context(skip_work_entries=True)
                    new_DraftAttendance = new_env['hr.draft.attendance']

                    # Re-browse open attendance in new env
                    open_att_id = open_att_id_map.get(emp_id)
                    open_attendance = new_HrAttendance.browse(open_att_id) if open_att_id else None
                    if open_attendance and open_attendance.check_out:
                        open_attendance = None

                    # Re-build existing_set for this employee in new env
                    emp_existing_set = {}
                    for key, att_id in existing_id_set.items():
                        if key[0] == emp_id:
                            emp_existing_set[key] = new_HrAttendance.browse(att_id)

                    # Select the processor function based on routing mode
                    if routing_mode == 'device_type':
                        processor = self._process_device_type_mode
                    elif routing_mode == 'forced_device':
                        processor = self._process_forced_device_mode
                    else:
                        processor = self._process_sequence_mode

                    last_punch_time = None
                    emp_marks = []

                    for dd in emp_drafts:
                        punch_time = dd['name']
                        draft_id = dd['id']
                        try:
                            # ── Anti-Duplicate Filter ──
                            if anti_dup_minutes > 0 and last_punch_time:
                                if (punch_time - last_punch_time) < anti_dup_delta:
                                    dedup_skipped += 1
                                    emp_marks.append((draft_id, None))
                                    continue

                            last_punch_time = punch_time
                            line = new_DraftAttendance.browse(draft_id)

                            # ── Route to the selected processor ──
                            marks, creates, open_attendance, was_skipped = processor(
                                line, open_attendance, emp_id, emp_name,
                                max_shift_hours, emp_existing_set, new_HrAttendance)

                            for draft_rec, att_id in marks:
                                emp_marks.append((draft_rec.id, att_id))

                            if was_skipped:
                                skipped_count += 1
                            else:
                                moved_count += 1

                        except Exception as e:
                            error_lines.append(f"{emp_name} @ {punch_time}: {str(e)}")
                            _logger.error(
                                'Error moving draft %s for %s: %s',
                                draft_id, emp_name, str(e))

                    # ── Mark this employee's drafts as moved ──
                    if emp_marks:
                        for draft_id, att_id in emp_marks:
                            vals = {'moved': True}
                            if att_id:
                                vals['moved_to'] = att_id
                            new_DraftAttendance.browse(draft_id).write(vals)

                    # Update open_att_id_map so cross-employee lookups
                    # (if any) stay correct
                    if open_attendance and not open_attendance.check_out:
                        open_att_id_map[emp_id] = open_attendance.id
                    else:
                        open_att_id_map.pop(emp_id, None)

                    new_cr.commit()
                except Exception:
                    new_cr.rollback()
                    raise
                finally:
                    new_cr.close()
            except Exception as e:
                error_lines.append(f"{emp_name}: transaction failed: {str(e)}")
                _logger.error(
                    'Transaction failed for employee %s: %s', emp_name, str(e))

            if (emp_idx + 1) % 50 == 0:
                _logger.info(
                    'Progress: %d/%d employees processed (moved: %d)',
                    emp_idx + 1, len(emp_ids_list), moved_count)

        # ──────────────────────────────────────────────────────────────
        # 5. SUMMARY
        # ──────────────────────────────────────────────────────────────
        msg = (
            f"Mode: {routing_mode} | "
            f"Moved: {moved_count} | "
            f"Skipped (dup): {skipped_count} | "
            f"Skipped (anti-dup): {dedup_skipped}"
        )
        _logger.info(msg)

        if error_lines:
            raise UserError(
                msg + "\n\nErrors encountered:\n" + "\n".join(error_lines))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Move Complete'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_generate_work_entries(self):
        """Manually trigger work entry generation for the selected dates/employees."""
        self.ensure_one()

        date_from = self.date1.date()
        date_to = self.date2.date()

        if self.employee_ids:
            employees = self.employee_ids
        else:
            versions = self.env['hr.employee']._get_all_versions_with_contract_overlap_with_period(
                date_from, date_to)
            employees = versions.mapped('employee_id')

        if not employees:
            raise UserError(_("No employees with active contracts found for this period."))

        we_success = 0
        error_lines = []

        _logger.info(
            'Generating work entries manually for %d employees (%s → %s)',
            len(employees), date_from, date_to)

        for emp in employees:
            try:
                version = emp._get_version(date=date_from)
                if not version:
                    error_lines.append(
                        f"{emp.name} (ID {emp.id}): No active version/contract")
                    continue

                if version.work_entry_source == 'attendance':
                    # Direct attendance → work entry (bypasses watermark bug)
                    version.generate_attendance_work_entries(date_from, date_to)
                else:
                    # Standard calendar pipeline
                    emp.generate_work_entries(date_from, date_to, force=True)
                we_success += 1
            except Exception as e:
                error_lines.append(f"{emp.name} (ID {emp.id}): {str(e)}")
                _logger.error(
                    'Failed to generate work entries for %s (ID %d): %s',
                    emp.name, emp.id, str(e))

        msg = f"Work Entries Generated: {we_success}/{len(employees)} OK"
        if error_lines:
            msg += f", {len(error_lines)} errors"

        _logger.info(msg)

        if error_lines:
            raise UserError(msg + "\n\nErrors:\n" + "\n".join(error_lines[:20]))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Work Entries Generated'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }
