# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    clinical_manager_id = fields.Many2one('hr.employee', string='Clinical Manager')

    def write(self, vals):
        res = super().write(vals)
        if 'clinical_manager_id' in vals:
            clinical_group = self.env.ref('thamar_hr_leaves.group_hr_holidays_clinical_manager')
            for company in self:
                old_manager = company._origin.clinical_manager_id
                new_manager = company.clinical_manager_id
                if old_manager and old_manager.user_id:
                    old_manager.user_id.write({'group_ids': [(3, clinical_group.id)]})
                if new_manager and new_manager.user_id:
                    new_manager.user_id.write({'group_ids': [(4, clinical_group.id)]})
        return res
