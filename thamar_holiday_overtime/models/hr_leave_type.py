# -*- coding: utf-8 -*-
from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    split_day_night = fields.Boolean(
        string='Split Day/Night Overtime',
        default=False,
        help='When enabled, work entries created from this leave type '
             'will have their duration split into Day Hours (6 AM – 9 PM) '
             'and Night Hours (9 PM – 6 AM) for overtime payroll calculation.',
    )
    day_start_hour = fields.Float(
        string='Day Start Hour',
        default=6.0,
        help='Hour when day shift starts (0-24)',
    )
    day_end_hour = fields.Float(
        string='Day End Hour',
        default=21.0,
        help='Hour when day shift ends (0-24)',
    )
