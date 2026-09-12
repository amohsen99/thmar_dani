# -*- coding: utf-8 -*-
"""Batch Generate Work Entries Wizard.

Uses the direct attendance-to-work-entry method from hr.version
for attendance-based employees.  Falls back to the standard Odoo
pipeline for calendar-based employees.

Processes employees in small batches (default 50) with per-employee
error isolation — no separate database cursors needed.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BATCH_SIZE = 50


class BatchGenerateWorkEntriesWizard(models.TransientModel):
    _name = 'batch.generate.work.entries.wizard'
    _description = 'Batch Generate Work Entries'

    date_from = fields.Date('From', required=True,
                            default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', required=True,
                          default=lambda self: fields.Date.today())
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees',
        help='Leave empty to generate for ALL employees with active contracts.')
    batch_size = fields.Integer(
        'Batch Size', default=BATCH_SIZE, required=True,
        help='Number of employees processed per iteration.')
    force = fields.Boolean(
        'Force Regenerate', default=True,
        help='If checked, existing non-validated work entries in the date '
             'range will be replaced. Recommended when entries are missing.')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_("'From' date must be before 'To' date."))

    def action_generate(self):
        """Main entry point — called from the wizard button."""
        self.ensure_one()
        date_from = self.date_from
        date_to = self.date_to
        batch_size = max(self.batch_size, 1)

        # Resolve target employees
        if self.employee_ids:
            employees = self.employee_ids
        else:
            versions = self.env['hr.employee']._get_all_versions_with_contract_overlap_with_period(
                date_from, date_to)
            employees = versions.mapped('employee_id')

        if not employees:
            raise UserError(_('No employees with active contracts found for this period.'))

        total = len(employees)
        _logger.info(
            'Batch work entry generation started: %d employees, '
            '%s → %s, batch_size=%d',
            total, date_from, date_to, batch_size)

        success_count = 0
        error_lines = []

        # Split employees into attendance-based and calendar-based
        att_employees = self.env['hr.employee']
        cal_employees = self.env['hr.employee']
        for emp in employees:
            version = emp._get_version(date=date_from)
            if version and version.work_entry_source == 'attendance':
                att_employees |= emp
            else:
                cal_employees |= emp

        # ── Phase 1: Attendance-based employees (direct method) ──
        if att_employees:
            _logger.info(
                'Phase 1: Processing %d attendance-based employees',
                len(att_employees))
            for idx in range(0, len(att_employees), batch_size):
                batch = att_employees[idx:idx + batch_size]
                for emp in batch:
                    try:
                        version = emp._get_version(date=date_from)
                        if not version:
                            error_lines.append(
                                f"{emp.name} (ID {emp.id}): No active version/contract")
                            continue
                        version.generate_attendance_work_entries(
                            date_from, date_to)
                        success_count += 1
                    except Exception as e:
                        error_lines.append(
                            f"{emp.name} (ID {emp.id}): {str(e)}")
                        _logger.error(
                            'Failed for attendance employee %s (ID %d): %s',
                            emp.name, emp.id, str(e))

                _logger.info(
                    'Attendance batch: %d/%d done',
                    min(idx + batch_size, len(att_employees)),
                    len(att_employees))

        # ── Phase 2: Calendar-based employees (standard Odoo pipeline) ──
        if cal_employees:
            _logger.info(
                'Phase 2: Processing %d calendar-based employees',
                len(cal_employees))
            for emp in cal_employees:
                try:
                    emp.generate_work_entries(
                        date_from, date_to, force=self.force)
                    success_count += 1
                except Exception as e:
                    error_lines.append(
                        f"{emp.name} (ID {emp.id}): {str(e)}")
                    _logger.error(
                        'Failed for calendar employee %s (ID %d): %s',
                        emp.name, emp.id, str(e))

        # Build summary
        msg = _(
            "Work entry generation complete.\n\n"
            "✓ Success: %(success)d / %(total)d employees\n"
            "  - Attendance-based: %(att)d\n"
            "  - Calendar-based: %(cal)d\n"
            "✗ Errors: %(errors)d",
            success=success_count, total=total,
            att=len(att_employees), cal=len(cal_employees),
            errors=len(error_lines))

        _logger.info(
            'Batch generation finished: %d/%d success, %d errors',
            success_count, total, len(error_lines))

        if error_lines:
            detail = "\n".join(error_lines[:50])
            if len(error_lines) > 50:
                detail += f"\n... and {len(error_lines) - 50} more errors"
            raise UserError(msg + "\n\n" + _("Errors:\n") + detail)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Work Entries Generated'),
                'message': msg,
                'type': 'success',
                'sticky': True,
            }
        }
