# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class hrDraftAttendance(models.Model):
    _name = 'hr.draft.attendance'
    _description = 'Draft Attendance'
    _order = 'name desc'

    name = fields.Datetime('Datetime', required=False)
    date = fields.Date('Date', required=False)
    day_name = fields.Char('Day')
    attendance_status = fields.Selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('sign_none', 'None')], 'Attendance State', required=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', index=True)
    lock_attendance = fields.Boolean('Lock Attendance')
    biometric_attendance_id = fields.Integer(string='Biometric Attendance ID')
    is_missing = fields.Boolean('Missing', default=False)
    moved = fields.Boolean(default=False, index=True)
    moved_to = fields.Many2one(comodel_name='hr.attendance', string='Moved to HR Attendance', index=True)
    device_id = fields.Many2one(
        comodel_name='biomteric.device.info',
        string='Source Device',
        index=True,
        help='The biometric device that produced this punch. Used by Dedicated Devices routing mode.',
    )

    # def unlink(self):
    #     for rec in self:
    #         if rec.moved == True:
    #             raise UserError(_("You can`t delete Moved Attendance"))
    #     return super().unlink()


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    last_draft_attendance_id = fields.Many2one('hr.draft.attendance', compute='_compute_last_draft_attendance_id', search='_search_last_draft_attendance_id')
    global_attendance_id = fields.Char(
        string='Global Attendance ID',
        tracking=True,
        help="If this employee uses the same attendance ID on all biometric devices, "
             "set it here instead of creating a separate record for each device. "
             "Per-device mappings (below) take priority over this global ID."
    )
    attendance_devices = fields.One2many('employee.attendance.devices', 'name', string='Attendance Devices')

    def _search_last_draft_attendance_id(self, operator, value):
        # Use a single SQL query to find employees whose latest draft attendance matches
        self.env.cr.execute("""
            SELECT DISTINCT da.employee_id
            FROM hr_draft_attendance da
            INNER JOIN (
                SELECT employee_id, MAX(id) AS max_id
                FROM hr_draft_attendance
                GROUP BY employee_id
            ) latest ON da.id = latest.max_id
            WHERE da.id %s %%s
        """ % ('IN' if operator == 'in' else '='), (tuple(value) if operator == 'in' else value,))
        emp_ids = [row[0] for row in self.env.cr.fetchall()]
        return [('id', 'in', emp_ids)]

    def _compute_last_draft_attendance_id(self):
        if not self.ids:
            return
        # Single SQL query to get the latest draft attendance for all employees at once
        self.env.cr.execute("""
            SELECT da.employee_id, da.id
            FROM hr_draft_attendance da
            INNER JOIN (
                SELECT employee_id, MAX(name) AS max_name
                FROM hr_draft_attendance
                WHERE employee_id IN %s
                GROUP BY employee_id
            ) latest ON da.employee_id = latest.employee_id AND da.name = latest.max_name
        """, (tuple(self.ids),))
        mapping = {}
        for emp_id, draft_id in self.env.cr.fetchall():
            mapping[emp_id] = draft_id
        for employee in self:
            employee.last_draft_attendance_id = mapping.get(employee.id, False)

    @api.depends('last_draft_attendance_id.attendance_status', 'last_draft_attendance_id', 'last_attendance_id.check_in', 'last_attendance_id.check_out', 'last_attendance_id')
    def _compute_attendance_state(self):
        if not self.ids:
            return super()._compute_attendance_state()

        # Batch-fetch which last_attendance_ids have been "moved" from draft
        att_ids = [e.last_attendance_id.id for e in self if e.last_attendance_id]
        moved_att_ids = set()
        if att_ids:
            self.env.cr.execute("""
                SELECT DISTINCT moved_to
                FROM hr_draft_attendance
                WHERE moved_to IN %s
            """, (tuple(att_ids),))
            moved_att_ids = {row[0] for row in self.env.cr.fetchall()}

        for employee in self:
            if employee.last_attendance_id and employee.last_attendance_id.id not in moved_att_ids:
                att = employee.last_attendance_id.sudo()
                employee.attendance_state = 'checked_in' if (att and not att.check_out) else 'checked_out'
            else:
                attendance_state = 'checked_out'
                if employee.last_draft_attendance_id and employee.last_draft_attendance_id.attendance_status == 'sign_in':
                    attendance_state = 'checked_in'
                employee.attendance_state = attendance_state


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    global_attendance_id = fields.Char(string='Global Attendance ID', readonly=True)


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
