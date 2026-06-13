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
        'Scheduled action function'
        machines = self.search([])
        for machine in machines:
            machine.download_attendance_sched()
            
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
        hr_attendance =  self.env['hr.draft.attendance']
        bunch_seconds = self.env['ir.config_parameter'].sudo().get_param('hr_attendance_zktecho.duplicate_punches_seconds')
        
        _logger.info('Fetching attendance')
        if self.fetch_days >= 0:
            now_datetime = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            prev_datetime = now_datetime - datetime.timedelta(days=self.fetch_days)
            curr_date = prev_datetime.date() 
        else:
            curr_date = datetime.datetime.strptime('1950-01-01','%Y-%m-%d').date()
        
        conn = None
        password = self.password or 0
        force_udp = False
        if self.protocol == 'udp':
            force_udp = True
        zk = ZK(self.ipaddress, port=self.portnumber, timeout=self.time_out, password=password, force_udp=force_udp, ommit_ping=self.ommit_ping)
        
        try:
            conn = zk.connect()
            conn.disable_device()
            attendance = conn.get_attendance()
            conn.enable_device()
            if (attendance):
                if self.fetch_days > 0:
                    now_datetime = conn.get_time()
                    prev_datetime = now_datetime - datetime.timedelta(days=self.fetch_days)
                    curr_date = prev_datetime.date()
                
                for lattendance in attendance:
                    if curr_date <= lattendance.timestamp.date():
                        
                        local_timezone = timezone(self.time_zone)
                        local_date = local_timezone.localize(lattendance.timestamp).astimezone(timezone('UTC'))
                        atten_time = datetime.datetime.strftime(local_date, DEFAULT_SERVER_DATETIME_FORMAT)
                        att_id = lattendance.user_id or ''
                        employees = self.env['employee.attendance.devices'].search([('attendance_id', '=', att_id), ('device_id', '=', self.id)])
                        try:
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
                            if action != False:
                                if not employees.name.id:
                                    _logger.info('No Employee record found to be associated with User ID: ' + str(att_id)+ ' on Finger Print Mahcine')
                                    continue
                                atten_ids = hr_attendance.search([('employee_id','=',employees.name.id), ('name','=',atten_time)])
                                atten_time = now_datetime = datetime.datetime.strptime(atten_time, DEFAULT_SERVER_DATETIME_FORMAT)
                                
                                time_with_seconds = atten_time - datetime.timedelta(seconds=float(bunch_seconds))
                                duplicated_recs = hr_attendance.search([('employee_id','=',employees.name.id),
                                                                        ('name','>',time_with_seconds),
                                                                        ('name','<=',atten_time)])
                                if duplicated_recs:
                                    continue
                                if atten_ids:
                                    _logger.info('Attendance For Employee' + str(employees.name.name)+ 'on Same time Exist')
                                    atten_ids.write({'name':atten_time,
                                                     'employee_id':employees.name.id,
                                                     'date':lattendance.timestamp.date(),
                                                     'attendance_status': action,
                                                     'day_name': lattendance.timestamp.strftime('%A')})
                                else:
                                    atten_id = hr_attendance.create({'name':atten_time,
                                                                     'employee_id':employees.name.id,
                                                                     'date':lattendance.timestamp.date(),
                                                                     'attendance_status': action,
                                                                     'day_name': lattendance.timestamp.strftime('%A')})
                                    _logger.info('Creating Draft Attendance Record: ' + str(atten_id) + 'For '+ str(employees.name.name))                                
                        except Exception as e:
                            _logger.error('Exception' + str(e))
                    else:
                        _logger.warning('Skip attendance because its before the threshold ' + str(curr_date))
            else:
                _logger.warning('No attendance Data to Fetch')
        except ZKNetworkError as e:
            if e.args[0] == "Device (ping %s) is Unreachable" % self.ipaddress:
                _logger.warning("Make sure the device (ping %s) is powered on and connected to the network" % self.ipaddress)
            else:
                _logger.warning(e)
        except ZKErrorResponse as e:
            if e.args[0] == 'Unauthenticated':
                _logger.warning("Unable to connect (Authentication Failure), Kindly supply correct password for the device.")
            else:
                _logger.warning(e)
        except timeout:
            _logger.warning("Connection timed out, make sure the device is turned on and not blocked by the Firewall")
        except Exception as e:
            _logger.warning(e)
        finally:
            if conn:
                conn.disconnect()
        return True

    def download_attendance_oldapi(self):
        hr_attendance =  self.env['hr.draft.attendance']
        bunch_seconds = self.env['ir.config_parameter'].sudo().get_param('hr_attendance_zktecho.duplicate_punches_seconds')
        
        _logger.info('Fetching attendance')
        if self.fetch_days >= 0:
            now_datetime = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            prev_datetime = now_datetime - datetime.timedelta(days=self.fetch_days)
            curr_date = prev_datetime.date() 
        else:
            curr_date = datetime.datetime.strptime('1950-01-01','%Y-%m-%d').date()
        
        conn = None
        password = self.password or 0
        force_udp = False
        if self.protocol == 'udp':
            force_udp = True
        zk = ZK(self.ipaddress, port=self.portnumber, timeout=self.time_out, password=password, force_udp=force_udp, ommit_ping=self.ommit_ping)
        
        try:
            conn = zk.connect()
            conn.disable_device()
            attendance = conn.get_attendance()
            conn.enable_device()
            if (attendance):
                if self.fetch_days > 0:
                    now_datetime = conn.get_time()
                    prev_datetime = now_datetime - datetime.timedelta(days=self.fetch_days)
                    curr_date = prev_datetime.date()
                
                for lattendance in attendance:
                    if curr_date <= lattendance.timestamp.date():
                        
                        local_timezone = timezone(self.time_zone)
                        local_date = local_timezone.localize(lattendance.timestamp).astimezone(timezone('UTC'))
                        atten_time = datetime.datetime.strftime(local_date, DEFAULT_SERVER_DATETIME_FORMAT)
                        att_id = lattendance.user_id or ''
                        employees = self.env['employee.attendance.devices'].search([('attendance_id', '=', att_id), ('device_id', '=', self.id)])
                        try:
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
                            if action != False:
                                if not employees.name.id:
                                    _logger.info('No Employee record found to be associated with User ID: ' + str(att_id)+ ' on Finger Print Mahcine')
                                    continue
                                atten_ids = hr_attendance.search([('employee_id','=',employees.name.id), ('name','=',atten_time)])
                                atten_time = now_datetime = datetime.datetime.strptime(atten_time, DEFAULT_SERVER_DATETIME_FORMAT)
                                
                                time_with_seconds = atten_time - datetime.timedelta(seconds=float(bunch_seconds))
                                duplicated_recs = hr_attendance.search([('employee_id','=',employees.name.id),
                                                                        ('name','>',time_with_seconds),
                                                                        ('name','<=',atten_time)])
                                if duplicated_recs:
                                    continue
                                if atten_ids:
                                    _logger.info('Attendance For Employee' + str(employees.name.name)+ 'on Same time Exist')
                                    atten_ids.write({'name':atten_time,
                                                     'employee_id':employees.name.id,
                                                     'date':lattendance.timestamp.date(),
                                                     'attendance_status': action,
                                                     'day_name': lattendance.timestamp.strftime('%A')})
                                else:
                                    atten_id = hr_attendance.create({'name':atten_time,
                                                                     'employee_id':employees.name.id,
                                                                     'date':lattendance.timestamp.date(),
                                                                     'attendance_status': action,
                                                                     'day_name': lattendance.timestamp.strftime('%A')})
                                    _logger.info('Creating Draft Attendance Record: ' + str(atten_id) + 'For '+ str(employees.name.name))                                
                        except Exception as e:
                            _logger.error('Exception' + str(e))
                    else:
                        _logger.warning('Skip attendance because its before the threshold ' + str(curr_date))
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