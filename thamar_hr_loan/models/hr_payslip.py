# -*- coding: utf-8 -*-
from datetime import time

from odoo import api, fields, models, Command


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.depends('employee_id', 'version_id', 'struct_id', 'date_from', 'date_to')
    def _compute_input_line_ids(self):
        """
        Extend payslip input computation to inject loan deduction amounts
        from confirmed loans with unpaid installments falling within the
        payslip period.
        """
        super()._compute_input_line_ids()

        loan_ded_type = self.env.ref(
            'thamar_hr_loan.input_loan_deduction', raise_if_not_found=False)

        if not loan_ded_type:
            return

        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                continue

            # Remove any existing loan deduction input lines (avoid duplicates)
            lines_to_remove = slip.input_line_ids.filtered(
                lambda x: x.input_type_id.id == loan_ded_type.id)
            input_line_vals = [Command.unlink(line.id) for line in lines_to_remove]

            # Find unpaid installments from confirmed loans within the payslip period
            loan_lines = self.env['hr.loan.line'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('loan_id.state', '=', 'confirm'),
                ('paid', '=', False),
                ('date', '>=', slip.date_from),
                ('date', '<=', slip.date_to),
            ])

            total_deduction = sum(loan_lines.mapped('amount'))

            if total_deduction > 0:
                input_line_vals.append(Command.create({
                    'name': 'Loan Deduction',
                    'amount': round(total_deduction, 2),
                    'input_type_id': loan_ded_type.id,
                }))

            if input_line_vals:
                slip.update({'input_line_ids': input_line_vals})

    def action_payslip_done(self):
        """
        When a payslip is confirmed, mark the corresponding loan installments
        as paid and link them to the payslip. Also check if the loan is
        fully paid to move it to 'done' state.
        """
        res = super().action_payslip_done()

        for slip in self:
            if not slip.employee_id:
                continue

            loan_lines = self.env['hr.loan.line'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('loan_id.state', '=', 'confirm'),
                ('paid', '=', False),
                ('date', '>=', slip.date_from),
                ('date', '<=', slip.date_to),
            ])

            for line in loan_lines:
                line.write({
                    'paid': True,
                    'payslip_id': slip.id,
                })

            # Check if any loan is now fully paid
            loans = loan_lines.mapped('loan_id')
            for loan in loans:
                if all(line.paid for line in loan.installment_ids):
                    loan.action_done()

        return res
