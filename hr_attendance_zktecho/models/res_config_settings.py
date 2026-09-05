# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_routing_mode = fields.Selection(
        selection=[
            ('sequence', 'Sequence-Based (Ignore device punch type, strictly follow In/Out order)'),
            ('device_type', 'Device-Driven (Depend on the punch type sent by the ZK device itself)'),
            ('forced_device', 'Dedicated Devices (Ignore ZK punch type, force Sign-In/Sign-Out based on device setting)'),
        ],
        string='Attendance Routing Mode',
        default='sequence',
        config_parameter='hr_attendance_zktecho.attendance_routing_mode',
        help="Controls how raw ZKTeco punches are converted to Odoo check-in/check-out records.\n"
             "• Sequence-Based: alternates In/Out regardless of what the device reports.\n"
             "• Device-Driven: uses the punch type (0=In, 1=Out) from the device log.\n"
             "• Dedicated Devices: each device is set to force only Sign-In or Sign-Out.",
    )

    attendance_max_shift_hours = fields.Integer(
        string='Max Shift Duration (hours)',
        default=20,
        config_parameter='hr_attendance_zktecho.attendance_max_shift_hours',
        help="Maximum allowed duration for a single attendance shift.\n"
             "Open attendances older than this will be auto-closed when a new punch arrives.",
    )

    attendance_anti_duplicate_minutes = fields.Integer(
        string='Anti-Duplicate Window (minutes)',
        default=5,
        config_parameter='hr_attendance_zktecho.attendance_anti_duplicate_minutes',
        help="Ignore duplicate punches from the same employee within this time window.\n"
             "Applied during both device download and attendance move operations.",
    )
