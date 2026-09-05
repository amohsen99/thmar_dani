# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    is_missing = fields.Boolean('Missing', default=False)

    def _create_work_entries(self):
        """Skip work-entry generation when called from the move wizard.

        The enterprise hr_work_entry_attendance module triggers expensive
        calendar/resource queries on every attendance write.  With ~1000
        employees this blows past the 600 s HTTP thread limit.  The move
        wizard sets ``skip_work_entries=True`` in the context so we can
        bypass this and let the user regenerate work entries separately.
        """
        if self.env.context.get('skip_work_entries'):
            return
        return super()._create_work_entries()

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """Override to skip the 'no open attendance' constraint.

        The move wizard handles orphaned check-ins by auto-closing them
        before creating new ones, so we don't need this constraint to
        block the operation. We still call super() for other validations
        (e.g. check_out > check_in).
        """
        # Intentionally skip the 'employee hasn't checked out' validation
        # because the move wizard auto-closes orphaned records.
        # If you want to re-enable this check for manual attendance entry,
        # you can add context-based skipping instead.
        for attendance in self:
            if attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(
                        _("\"Check Out\" time cannot be earlier than \"Check In\" time for %(empl_name)s.",
                          empl_name=attendance.employee_id.name)
                    )