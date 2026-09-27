from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref('hr_attendance_zktecho.biometric_attendances', raise_if_not_found=False)
    # The former XML was noupdate and installed an inactive daily job.
    if cron and cron.code == 'model.fetch_attendance()':
        cron.write({
            'name': 'ZKTeco: Download Device Attendances',
            'code': 'model._cron_download_attendance()',
            'interval_number': 5, 'interval_type': 'minutes',
            'active': True, 'user_id': SUPERUSER_ID, 'priority': 5,
        })
