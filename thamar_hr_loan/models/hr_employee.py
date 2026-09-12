# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    loan_count = fields.Integer(
        string='Loan Count',
        compute='_compute_loan_count',
    )

    def _compute_loan_count(self):
        loan_data = self.env['hr.loan'].read_group(
            domain=[
                ('employee_id', 'in', self.ids),
                ('state', 'not in', ('refused',)),
            ],
            fields=['employee_id'],
            groupby=['employee_id'],
        )
        mapped_data = {
            item['employee_id'][0]: item['employee_id_count']
            for item in loan_data
        }
        for employee in self:
            employee.loan_count = mapped_data.get(employee.id, 0)

    def action_open_loans(self):
        """Open the list of loans for this employee."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Loans',
            'res_model': 'hr.loan',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
