# -*- coding: utf-8 -*-
import logging

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    @api.constrains('duration')
    def _check_duration(self):
        """Override to clamp invalid durations instead of crashing.

        The default Odoo constraint raises a hard ValidationError when
        duration <= 0 or > 24.  This can block the entire Work Entries
        view when auto-generated entries (from attendance or calendar)
        produce edge-case values (e.g. overlapping shifts that sum to
        > 24 h, or zero-length leave entries).

        Instead of crashing, we silently clamp the value and log a
        warning so the HR team can investigate the root attendance data.
        """
        for work_entry in self:
            if float_compare(work_entry.duration, 0, 3) <= 0:
                _logger.warning(
                    "Work entry %s (employee %s, date %s) had duration %.4f <= 0. "
                    "Clamped to 0.01 to avoid crash. Please check source attendance data.",
                    work_entry.id, work_entry.employee_id.name,
                    work_entry.date, work_entry.duration,
                )
                work_entry.duration = 0.01
            elif float_compare(work_entry.duration, 24, 3) > 0:
                _logger.warning(
                    "Work entry %s (employee %s, date %s) had duration %.4f > 24. "
                    "Clamped to 24 to avoid crash. Please check source attendance data.",
                    work_entry.id, work_entry.employee_id.name,
                    work_entry.date, work_entry.duration,
                )
                work_entry.duration = 24.0
