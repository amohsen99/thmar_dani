# -*- coding: utf-8 -*-

import datetime
from pytz import timezone, all_timezones
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging
from zk import ZK
from zk.exception import ZKErrorResponse, ZKNetworkError
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from socket import timeout
_logger = logging.getLogger('biometric_device')

class BiomtericDeviceInfo(models.Model):
    _name = 'biomteric.device.info'
    _description = 'Biomteric Device Info'
    _inherit = ['mail.thread']

    @api.model
    def fetch_attendance(self):
        return self._cron_download_attendance()

    def test_connection_device(self):
        force_udp = False
        if self.protocol == 'udp':
            force_udp = True
            
        password = self.password or 0
        zk = ZK(self.ipaddress, port=self.portnumber, timeout=self.time_out, password=password, force_udp=force_udp, ommit_ping=self.ommit_ping)
        
        res = None
        try:
            res = zk.connect()
            if not res:
                raise UserError(_('Connection Failed to Device '+str(self.name)))
            else:
                raise UserError(_('Connection Successful '+str(self.name)))
        except ZKNetworkError as e:
            if e.args[0] == "Device (ping %s) is Unreachable" % self.ipaddress:
                raise UserError(_("Make sure the device (ping %s) is powered on and connected to the network" % self.ipaddress))
            else:
                raise UserError(e)
        except ZKErrorResponse as e:
            if e.args[0] == 'Unauthenticated':
                raise UserError(_("Unable to connect (Authentication Failure), Kindly supply correct password for the device."))
            else:
                raise UserError(e)
        except timeout:
            raise UserError(_("Connection timed out, make sure the device is turned on and not blocked by the Firewall"))
        except Exception as e:
            raise UserError(e)
        finally:
            if res:
                res.disconnect()

    def download_attendance_sched(self):
        # Keep existing scheduled-action integrations on the same download path.
        return self.download_attendance_oldapi()

    def download_attendance_oldapi(self):
        self.ensure_one()
        if not self._lock_attendance_sync():
            raise UserError(_('Another attendance download or move is running. Please retry shortly.'))
        hr_attendance = self.env['hr.draft.attendance']
        anti_dup_minutes = self.env['ir.config_parameter'].sudo().get_param('hr_attendance_zktecho.attendance_anti_duplicate_minutes', '5')
        bunch_seconds = float(anti_dup_minutes) * 60

        _logger.info('Fetching attendance')
        # Date range fields take priority over fetch_days
        sync_from = self.env.context.get('zk_sync_from', self.sync_date_from)
        sync_to = self.env.context.get('zk_sync_to', self.sync_date_to)
        use_date_range = sync_from or sync_to
        if use_date_range:
            sync_from = sync_from or datetime.datetime(1950, 1, 1)
            sync_to = sync_to or datetime.datetime(2099, 12, 31, 23, 59, 59)
            curr_date = sync_from.date()
            _logger.info('Using date range filter: %s to %s', sync_from, sync_to)
        elif self.fetch_days >= 0:
            now_datetime = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            prev_datetime = now_datetime - datetime.timedelta(days=self.fetch_days)
            curr_date = prev_datetime.date()
        else:
            curr_date = datetime.datetime.strptime('1950-01-01', '%Y-%m-%d').date()

        conn = None
        password = self.password or 0
        force_udp = False
        if self.protocol == 'udp':
            force_udp = True
        zk = ZK(self.ipaddress, port=self.portnumber, timeout=self.time_out, password=password, force_udp=force_udp, ommit_ping=self.ommit_ping)

        try:
            conn = zk.connect()
            attendance = conn.get_attendance()
            if (attendance):
                if not use_date_range and self.fetch_days > 0:
                    now_datetime = conn.get_time()
                    prev_datetime = now_datetime - datetime.timedelta(days=self.fetch_days)
                    curr_date = prev_datetime.date()

                # --- Pre-cache employee lookups ---
                # Build global_attendance_id -> employee.id map
                all_employees = self.env['hr.employee'].search([('global_attendance_id', '!=', False)])
                global_id_map = {emp.global_attendance_id: emp.id for emp in all_employees}

                # Build device-specific (att_id) -> employee.id map
                device_mappings = self.env['employee.attendance.devices'].search([('device_id', '=', self.id)])
                device_id_map = {rec.attendance_id: rec.name.id for rec in device_mappings}

                def resolve_employee(att_id):
                    """Resolve attendance user_id to employee.id using cached maps."""
                    emp_id = global_id_map.get(att_id)
                    if not emp_id:
                        emp_id = device_id_map.get(att_id)
                    return emp_id

                # --- Pre-fetch existing attendance for duplicate checking ---
                existing_attendance = hr_attendance.search([
                    ('name', '>=', (sync_from if use_date_range else datetime.datetime.combine(curr_date, datetime.time.min)) - datetime.timedelta(days=1)),
                ])
                # Build a set of (employee_id, name_str) for fast lookup
                existing_set = set()
                for rec in existing_attendance:
                    existing_set.add((rec.employee_id.id, str(rec.name)))

                # Build a dict of (employee_id) -> sorted list of datetimes for bunch-seconds check
                from collections import defaultdict
                existing_times = defaultdict(list)
                for rec in existing_attendance:
                    existing_times[rec.employee_id.id].append(rec.name)

                # --- Pre-cache employee names ---
                emp_ids_set = set(global_id_map.values()) | set(device_id_map.values())
                emp_name_map = {}
                if emp_ids_set:
                    for emp in self.env['hr.employee'].browse(list(emp_ids_set)):
                        emp_name_map[emp.id] = emp.name

                # --- Process attendance records ---
                vals_to_create = []
                bunch_secs = bunch_seconds

                for lattendance in sorted(attendance, key=lambda punch: punch.timestamp):
                    if not use_date_range and curr_date > lattendance.timestamp.date():
                        continue
                    local_timezone = timezone(self.time_zone)
                    local_date = local_timezone.localize(lattendance.timestamp).astimezone(timezone('UTC'))
                    atten_time_str = datetime.datetime.strftime(local_date, DEFAULT_SERVER_DATETIME_FORMAT)
                    atten_time = datetime.datetime.strptime(atten_time_str, DEFAULT_SERVER_DATETIME_FORMAT)
                    if use_date_range and not sync_from <= atten_time <= sync_to:
                        continue
                    att_id = str(lattendance.user_id or '')

                    employee_id_val = resolve_employee(att_id)
                    if not employee_id_val:
                        _logger.info('No Employee record found to be associated with User ID: ' + str(att_id) + ' on Finger Print Machine')
                        continue

                    try:
                        # Force action overrides device punch type
                        if self.force_action:
                            action = self.force_action
                        else:
                            punch_flag = lattendance.punch
                            if self.api_type == 'legacy':
                                punch_flag = lattendance.status

                            if self.action == 'both':
                                if str(punch_flag) in list(self.sign_in):
                                    action = 'sign_in'
                                elif str(punch_flag) in list(self.sign_out):
                                    action = 'sign_out'
                                else:
                                    action = 'sign_none'
                            else:
                                action = self.action

                        if action == False:
                            continue

                        # Check exact duplicate in pre-fetched set
                        if (employee_id_val, str(atten_time)) in existing_set:
                            emp_name = emp_name_map.get(employee_id_val, att_id)
                            _logger.info('Attendance For Employee ' + str(emp_name) + ' on Same time Exist')
                            continue

                        # Check bunch-seconds duplicate in pre-fetched times
                        if bunch_secs > 0:
                            time_threshold = atten_time - datetime.timedelta(seconds=bunch_secs)
                            emp_times = existing_times.get(employee_id_val, [])
                            is_duplicate = False
                            for t in emp_times:
                                if time_threshold < t <= atten_time:
                                    is_duplicate = True
                                    break
                            if is_duplicate:
                                continue

                        vals = {
                            'name': atten_time,
                            'employee_id': employee_id_val,
                            'date': lattendance.timestamp.date(),
                            'attendance_status': action,
                            'day_name': lattendance.timestamp.strftime('%A'),
                            'device_id': self.id,
                        }
                        vals_to_create.append(vals)

                        # Track the new record in memory to avoid creating duplicates within same batch
                        existing_set.add((employee_id_val, str(atten_time)))
                        existing_times[employee_id_val].append(atten_time)

                        emp_name = emp_name_map.get(employee_id_val, att_id)
                        _logger.info('Prepared Draft Attendance Record For ' + str(emp_name))

                    except Exception as e:
                        raise UserError(_('Cannot import device punch: %s') % e) from e

                # --- Batch create in chunks ---
                BATCH_SIZE = 500
                total = len(vals_to_create)
                _logger.info('Creating %d draft attendance records in batches of %d', total, BATCH_SIZE)
                for i in range(0, total, BATCH_SIZE):
                    batch = vals_to_create[i:i + BATCH_SIZE]
                    hr_attendance.create(batch)
                    # Flush and clear cache to free memory between batches
                    self.env.cr.flush()
                    self.env.invalidate_all()
                    _logger.info('Created batch %d-%d of %d', i + 1, min(i + BATCH_SIZE, total), total)

                _logger.info('Finished creating %d draft attendance records', total)
            else:
                _logger.warning('No attendance Data to Fetch')
        except ZKNetworkError as e:
            _logger.error(e.args[0])
            if e.args[0] == "Device (ping %s) is Unreachable" % self.ipaddress:
                raise UserError(_("Make sure the device (ping %s) is powered on and connected to the network" % self.ipaddress))
            else:
                raise UserError(e)
        except ZKErrorResponse as e:
            if e.args[0] == 'Unauthenticated':
                raise UserError(_("Unable to connect (Authentication Failure), Kindly supply correct password for the device."))
            else:
                raise UserError(e)
        except timeout:
            raise UserError(_("Connection timed out, make sure the device is turned on and not blocked by the Firewall"))
        except Exception as e:
            raise UserError(e)
        finally:
            if conn:
                conn.disconnect()
        return True

    name = fields.Char(string='Device', required=True, tracking=True)
    ipaddress = fields.Char(string='IP Address', required=True, help="Enter the IP address of the device or network.", tracking=True)
    portnumber = fields.Integer(string='Port', required=True, default=4370, help="Port which allows connection to the "
                                                                                 "device", tracking=True)
    fetch_days = fields.Integer('Attendance Fetching Limit (days)', default=-1,
                                help="If -1 means all attendances will be fetched otherwise will get the attendance "
                                     "from last number of days specified", tracking=True)
    action = fields.Selection(selection=[('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('both', 'All')],
                              string='Action', default='both', required=True, help="Actions Performed on the "
                                                                                      "machine whether sign-in or "
                                                                                      "sign-out or both", tracking=True)
    time_zone = fields.Selection('_tz_get', string='Timezone', required=True, default=lambda self: self.env.user.tz or 'UTC', help="Select the timezone for your location or the desired time zone for the system.", tracking=True)
    password = fields.Char('Password', tracking=True, help="Specify password if the biometric device is password protected")
    protocol = fields.Selection(selection=[('tcp', 'TCP'), ('udp', 'UDP')], string='Protocol', required=True, default='tcp', help="UDP is good for older devices with smaller amounts of data, TCP should be used with devices that have larger amounts of data", tracking=True)
    ommit_ping = fields.Boolean(string='Omit Ping', default=True, help="Do not attempt to ping the IP before connecting to the device", tracking=True)
    api_type = fields.Selection(selection=[('legacy', 'Legacy API'), ('new', 'New API')], string='API Type', default='new', help="Legacy API is used by older devices, New API is used by modern devices which usually support face recognition as well. Using wrong API will result in invalid attendance status.", tracking=True)
    sign_in = fields.Char('Sign In Parameters', required=True, default='0,2,4', help="Enter the IP address", tracking=True)
    sign_out = fields.Char('Sign Out Parameters', required=True, default='1,3,5', help="Enter the IP address", tracking=True)
    time_out = fields.Integer('Time Out Limit (Sec)', default=60, help="Specify the time at which the session ends.", tracking=True)
    sync_date_from = fields.Datetime('Sync Date From', help="If set, only sync attendance records from this date/time. Overrides 'Attendance Fetching Limit'.")
    sync_date_to = fields.Datetime('Sync Date To', help="If set, only sync attendance records up to this date/time. Overrides 'Attendance Fetching Limit'.")
    force_action = fields.Selection(
        selection=[('sign_in', 'Sign In'), ('sign_out', 'Sign Out')],
        string='Force Action',
        help="If set, all attendance records from this device will be forced to this action, ignoring the punch type reported by the device.",
        tracking=True,
    )
    
    @api.model
    def _tz_get(self):
        return [(x, x) for x in all_timezones]
    
    @api.constrains('ipaddress', 'portnumber')
    def _check_unique_constraint(self):
        self.ensure_one()
        record = self.search([('ipaddress', '=', self.ipaddress), ('portnumber', '=', self.portnumber)])
        if len(record) > 1:
            raise ValidationError('Device already exists with IP ('+str(self.ipaddress)+') and port ('+str(self.portnumber)+')!')

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _("%s (copy)") % (self.name or '')
        default['ipaddress'] = _("%s (copy)") % (self.ipaddress or '')
        default['portnumber'] = self.portnumber
        return super().copy(default)
