from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Existing scheduled actions are protected by noupdate in the XML.
    for name in ('biometric_attendances', 'cron_move_draft_attendances'):
        cron = env.ref(f'hr_attendance_zktecho.{name}', raise_if_not_found=False)
        if cron:
            cron.write({'interval_number': 2, 'interval_type': 'hours'})
