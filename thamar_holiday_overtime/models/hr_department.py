from odoo import api, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    @api.model_create_multi
    def create(self, vals_list):
        departments = super().create(vals_list)
        departments._sync_overtime_approver_groups()
        return departments

    def write(self, vals):
        result = super().write(vals)
        if {'supervisor_id', 'manager_id'} & set(vals):
            self._sync_overtime_approver_groups()
        return result

    @api.model
    def _sync_overtime_approver_groups(self):
        """Keep department approvers able to open their team requests."""
        group = self.env.ref('thamar_holiday_overtime.group_overtime_manager')
        departments = self.sudo().search([])
        approvers = (departments.mapped('supervisor_id.user_id') | departments.mapped('manager_id.user_id')).filtered(
            lambda user: user.id and not user.share
        )
        users_to_remove = group.user_ids - approvers
        if users_to_remove:
            users_to_remove.write({'group_ids': [(3, group.id)]})
        missing_users = approvers - group.user_ids
        if missing_users:
            missing_users.write({'group_ids': [(4, group.id)]})
