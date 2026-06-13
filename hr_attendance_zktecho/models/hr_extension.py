# -*- coding: utf-8 -*-

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError, UserError


class hrDraftAttendance(models.Model):
    _name = 'hr.draft.attendance'
    _description = 'Draft Attendance'
    _inherit = ['mail.thread']
    _order = 'name desc'
    
    name = fields.Datetime('Datetime', required=False, tracking=True)
    date = fields.Date('Date', required=False,tracking=True)
    day_name = fields.Char('Day',tracking=True)
    attendance_status = fields.Selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('sign_none', 'None')], 'Attendance State', required=True,tracking=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',tracking=True)
    lock_attendance = fields.Boolean('Lock Attendance',tracking=True)
    biometric_attendance_id = fields.Integer(string='Biometric Attendance ID',tracking=True)
    is_missing = fields.Boolean('Missing', default=False,tracking=True)
    moved = fields.Boolean(default=False)
    moved_to = fields.Many2one(comodel_name='hr.attendance', string='Moved to HR Attendance')
    
    def unlink(self):
        for rec in self:
            if rec.moved == True:
                raise UserError(_("You can`t delete Moved Attendance"))
        return super().unlink()
    
    
class HrEmployee(models.Model):
    _inherit = "hr.employee"
    
    last_draft_attendance_id = fields.Many2one('hr.draft.attendance', compute='_compute_last_draft_attendance_id', search='_search_last_draft_attendance_id')
    attendance_devices = fields.One2many('employee.attendance.devices', 'name', string='Attendance Devices')
    
    def _search_last_draft_attendance_id(self, operator, value):
        records = self.search([])
        if operator == 'in':
            records = records.filtered(lambda r: r.last_draft_attendance_id.id in value)
        elif operator == '=':
            records = records.filtered(lambda r: r.last_draft_attendance_id.id == value)
        else:
            raise NotImplementedError()
        return [('id', 'in', records.ids)]

    def _compute_last_draft_attendance_id(self):
        for employee in self:
            draft_atts = self.env['hr.draft.attendance'].search([('employee_id','=',employee.id)], order='name desc')
            employee.last_draft_attendance_id = draft_atts.ids

    @api.depends('last_draft_attendance_id.attendance_status', 'last_draft_attendance_id', 'last_attendance_id.check_in', 'last_attendance_id.check_out', 'last_attendance_id')
    def _compute_attendance_state(self):
        for employee in self:
            if employee.last_attendance_id and not self.env['hr.draft.attendance'].search([('moved_to','=',employee.last_attendance_id.id),
                                                                                           ('employee_id','=',employee.id)]):
                att = employee.last_attendance_id.sudo()
                employee.attendance_state = att and not att.check_out and 'checked_in' or 'checked_out'
            else:
                attendance_state = 'checked_out'
                if employee.last_draft_attendance_id and employee.last_draft_attendance_id.attendance_status == 'sign_in':
                    attendance_state = 'checked_in'
                employee.attendance_state = attendance_state
            
class EmployeeAttendanceDevices(models.Model):
    _name = 'employee.attendance.devices'
    _description = 'Employee Attendance Devices'
    
    name = fields.Many2one(comodel_name='hr.employee', string='Employee', readonly=True)
    attendance_id = fields.Char("Attendance ID", required=True)
    device_id = fields.Many2one(comodel_name='biomteric.device.info', string='Biometric Device', required=True, ondelete='restrict')
    
    @api.constrains('attendance_id', 'device_id', 'name')
    def _check_unique_constraint(self):
        for rec in self:
            record = self.search([('attendance_id', '=', rec.attendance_id), ('device_id', '=', rec.device_id.id)])
            if len(record) > 1:
                raise ValidationError('Employee with Id ('+ str(rec.attendance_id)+') exists on Device ('+ str(rec.device_id.name)+') !')
            record = self.search([('name', '=', rec.name.id), ('device_id', '=', rec.device_id.id)])
            if len(record) > 1:
                raise ValidationError('Configuration for Device ('+ str(rec.device_id.name)+') of Employee  ('+ str(rec.name.name)+') already exists!')
