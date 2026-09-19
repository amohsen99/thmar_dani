# -*- coding: utf-8 -*-
from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    supervisor_id = fields.Many2one('hr.employee', string='Department Supervisor', help='The supervisor responsible for initial time off approvals within the department.')

    def write(self, vals):
        res = super().write(vals)
        time_off_groups = [self.env.ref(xmlid, raise_if_not_found=False) for xmlid in (
            'hr_holidays.group_hr_holidays_user', 'hr_holidays.group_hr_holidays_manager',
            'hr_holidays.group_hr_holidays_responsible',
        )]
        time_off_groups = [group for group in time_off_groups if group]
        if 'supervisor_id' in vals:
            self._update_leave_approver_groups('supervisor_id', 'thamar_hr_leaves.group_hr_holidays_department_supervisor', time_off_groups)
        if 'manager_id' in vals:
            self._update_leave_approver_groups('manager_id', 'thamar_hr_leaves.group_hr_holidays_department_manager', time_off_groups)
        return res

    def _update_leave_approver_groups(self, field_name, group_xmlid, time_off_groups):
        approver_group = self.env.ref(group_xmlid)
        for department in self:
            old_employee = department._origin[field_name]
            new_employee = department[field_name]
            if old_employee and old_employee.user_id:
                old_employee.user_id.write({'group_ids': [(3, approver_group.id)] + [(3, group.id) for group in time_off_groups]})
            if new_employee and new_employee.user_id:
                new_employee.user_id.write({'group_ids': [(4, approver_group.id)] + [(3, group.id) for group in time_off_groups]})
