# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger('biometric_device')


class DownloadAllDevicesWizard(models.TransientModel):
    _name = 'download.all.devices.wizard'
    _description = 'Download Attendance From All Devices'

    date_from = fields.Datetime('From', required=True)
    date_to = fields.Datetime('To', required=True)

    def action_download(self):
        """Download attendance from ALL devices using the wizard date range."""
        self.ensure_one()
        machines = self.env['biomteric.device.info'].search([])
        if not machines:
            raise UserError(_('No biometric devices configured.'))

        errors = []
        success_count = 0
        for machine in machines:
            # Save original date range values
            orig_from = machine.sync_date_from
            orig_to = machine.sync_date_to
            try:
                # Temporarily set the wizard's date range on the device
                machine.write({
                    'sync_date_from': self.date_from,
                    'sync_date_to': self.date_to,
                })
                machine.download_attendance_oldapi()
                success_count += 1
            except Exception as e:
                errors.append("%s (%s): %s" % (machine.name, machine.ipaddress, str(e)))
                _logger.error('Failed to download from device %s: %s', machine.name, str(e))
            finally:
                # Restore original date range values
                machine.write({
                    'sync_date_from': orig_from,
                    'sync_date_to': orig_to,
                })

        if errors:
            raise UserError(
                _("Download completed with errors:\n\n%s") % "\n".join(errors))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Download Complete'),
                'message': _('Attendance downloaded from %d device(s).') % success_count,
                'type': 'success',
                'sticky': False,
            }
        }
