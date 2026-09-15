# -*- coding: utf-8 -*-
"""Monthly accrual validation for leave requests.

Enforces the rule: employees can only take leave up to their
accrued monthly balance (Total Days / 12 × months elapsed).
"""
import logging
from datetime import datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    # Retain the existing model and technical field names: this changes
    # declaration ownership only, never the hr_leave database columns.
    accrual_limit_override = fields.Boolean(string='Override Monthly Accrual Limit', help='Allow this leave request to exceed the monthly accrual limit. Requires HR approval.')
    department_supervisor_id = fields.Many2one('hr.employee', related='department_id.supervisor_id', string='Department Supervisor', store=True, readonly=True)
    department_manager_id = fields.Many2one('hr.employee', related='department_id.manager_id', string='Department Manager', store=True, readonly=True)
    supervisor_approved = fields.Boolean(string='Supervisor Approved', default=False, copy=False)
    manager_approved = fields.Boolean(string='Manager Approved', default=False, copy=False)
    can_supervisor_approve = fields.Boolean(compute='_compute_can_supervisor_approve')
    can_manager_approve = fields.Boolean(compute='_compute_can_manager_approve')
    requires_clinical_approval = fields.Boolean(related='holiday_status_id.requires_clinical_approval', readonly=True)
    clinical_approved = fields.Boolean(string='Clinical Approved', default=False, copy=False)
    can_clinical_approve = fields.Boolean(compute='_compute_can_clinical_approve')
    clinical_manager_id = fields.Many2one('hr.employee', related='company_id.clinical_manager_id', store=True, readonly=True)

    def _check_accrual_override_access(self, values_list):
        """Only a Time Off officer may grant the exceptional accrual override."""
        if any(values.get('accrual_limit_override') for values in values_list) and (
            not self.env.su
            and not self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        ):
            raise AccessError(_('Only a Time Off officer can override the monthly accrual limit.'))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_accrual_override_access(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        self._check_accrual_override_access([vals])
        return super().write(vals)

    @api.depends('state', 'department_supervisor_id', 'supervisor_approved')
    def _compute_can_supervisor_approve(self):
        for leave in self:
            is_supervisor = leave.department_id.supervisor_id and leave.department_id.supervisor_id.user_id == self.env.user
            leave.can_supervisor_approve = leave.state == 'confirm' and is_supervisor and not leave.supervisor_approved

    @api.depends('state', 'department_manager_id', 'manager_approved', 'supervisor_approved')
    def _compute_can_manager_approve(self):
        for leave in self:
            is_manager = leave.department_id.manager_id and leave.department_id.manager_id.user_id == self.env.user
            supervisor_ok = not leave.department_id.supervisor_id or leave.supervisor_approved
            # Department approvals do not use Odoo's ``validate1`` state.
            # That state belongs to Odoo's own optional double-validation
            # workflow and would let the next approver validate the leave.
            leave.can_manager_approve = leave.state == 'confirm' and is_manager and not leave.manager_approved and supervisor_ok

    def action_supervisor_approve(self):
        for leave in self:
            if not leave.can_supervisor_approve:
                raise UserError(_('You are not authorized to perform this action or the leave is not in the correct state.'))
            leave.write({'supervisor_approved': True})
            leave.message_post(body=_('Department Supervisor approved the leave request.'))
        return True

    def action_supervisor_refuse(self):
        for leave in self:
            if not leave.can_supervisor_approve:
                raise UserError(_('You are not authorized to perform this action or the leave is not in the correct state.'))
            # Base Odoo only lets Time Off officers refuse.  Authorization
            # above is department-scoped; sudo is limited to this record.
            leave.sudo().action_refuse()
            leave.message_post(body=_('Department Supervisor refused the leave request.'))
        return True

    def action_manager_approve(self):
        for leave in self:
            if not leave.can_manager_approve:
                raise UserError(_('You are not authorized to perform this action or the leave is not in the correct state.'))
            leave.write({'manager_approved': True})
            leave.message_post(body=_('Department Manager approved the leave request.'))
        return True

    def action_manager_refuse(self):
        for leave in self:
            if not leave.can_manager_approve:
                raise UserError(_('You are not authorized to perform this action or the leave is not in the correct state.'))
            # Base Odoo only lets Time Off officers refuse.  Authorization
            # above is department-scoped; sudo is limited to this record.
            leave.sudo().action_refuse()
            leave.message_post(body=_('Department Manager refused the leave request.'))
        return True

    @api.depends('state', 'department_supervisor_id', 'supervisor_approved', 'requires_clinical_approval', 'clinical_approved', 'department_manager_id', 'manager_approved')
    def _compute_can_clinical_approve(self):
        for leave in self:
            is_clinical_manager = leave.company_id.clinical_manager_id and leave.company_id.clinical_manager_id.user_id == self.env.user
            supervisor_ok = not leave.department_id.supervisor_id or leave.supervisor_approved
            manager_ok = not leave.department_id.manager_id or leave.manager_approved
            leave.can_clinical_approve = leave.state == 'confirm' and leave.requires_clinical_approval and is_clinical_manager and not leave.clinical_approved and supervisor_ok and manager_ok

    def action_clinical_approve(self):
        for leave in self:
            if not leave.can_clinical_approve:
                raise UserError(_('You are not authorized to perform this action or the leave is not in the correct state.'))
            leave.write({'clinical_approved': True})
            leave.message_post(body=_('Clinical Manager approved the ill leave request.'))
        return True

    def action_clinical_refuse(self):
        for leave in self:
            if not leave.can_clinical_approve:
                raise UserError(_('You are not authorized to perform this action or the leave is not in the correct state.'))
            leave.action_refuse()
            leave.message_post(body=_('Clinical Manager refused the ill leave request.'))
        return True

    @api.depends('state', 'employee_id', 'department_id', 'department_supervisor_id', 'supervisor_approved', 'requires_clinical_approval', 'clinical_approved', 'department_manager_id', 'manager_approved')
    def _compute_can_approve(self):
        super()._compute_can_approve()
        for leave in self:
            supervisor_pending = leave.department_id.supervisor_id and not leave.supervisor_approved
            manager_pending = leave.department_id.manager_id and not leave.manager_approved
            if supervisor_pending or manager_pending:
                leave.can_approve = False
            if leave.requires_clinical_approval and leave.company_id.clinical_manager_id and not leave.clinical_approved:
                leave.can_approve = False

    @api.depends('state', 'employee_id', 'department_id', 'department_supervisor_id', 'supervisor_approved', 'requires_clinical_approval', 'clinical_approved', 'department_manager_id', 'manager_approved')
    def _compute_can_validate(self):
        super()._compute_can_validate()
        for leave in self:
            supervisor_pending = leave.department_id.supervisor_id and not leave.supervisor_approved
            manager_pending = leave.department_id.manager_id and not leave.manager_approved
            if supervisor_pending or manager_pending:
                leave.can_validate = False
            if leave.requires_clinical_approval and leave.company_id.clinical_manager_id and not leave.clinical_approved:
                leave.can_validate = False

    @api.constrains('date_from', 'holiday_status_id', 'employee_id')
    def _check_appointment_month_eligibility(self):
        """Annual and casual leave cannot be taken during the hire month."""
        if self.env.context.get('skip_thamar_leave_policy_checks'):
            return
        Allocation = self.env['hr.leave.allocation']
        for leave in self:
            leave_type = leave.holiday_status_id
            if (
                leave.state in ('refuse', 'cancel')
                or not leave.employee_id
                or not leave.date_from
                or not (leave_type.is_annual_leave or leave_type.is_casual_leave)
            ):
                continue

            request_date = fields.Datetime.to_datetime(leave.date_from).date()
            first_eligible_date = Allocation._first_eligible_leave_date(
                leave.employee_id, request_date.year,
            )
            if not first_eligible_date or request_date < first_eligible_date:
                raise ValidationError(_(
                    "%(leave_type)s is not available during the employee's appointment month. "
                    "The first eligible date is %(first_date)s.",
                    leave_type=leave_type.name,
                    first_date=first_eligible_date or _('the next leave year'),
                ))

    @api.constrains('date_from', 'date_to', 'holiday_status_id', 'employee_id', 'number_of_days', 'accrual_limit_override')
    def _check_monthly_accrual_cap(self):
        """Block leave requests that exceed the monthly rate unless HR overrides."""
        if self.env.context.get('skip_thamar_leave_policy_checks'):
            return
        for leave in self:
            if leave.state in ('refuse', 'cancel'):
                continue

            leave_type = leave.holiday_status_id
            if not leave_type.use_monthly_accrual:
                continue

            if not leave.employee_id or not leave.date_from:
                continue

            year = leave.date_from.year

            allocations = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'),
                ('leave_year', '=', year),
            ])
            total_allocated = sum(allocations.mapped('number_of_days'))
            if not total_allocated:
                continue

            leave_id = leave._origin.id if leave._origin else leave.id
            domain = [
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', 'not in', ('refuse', 'cancel')),
                ('date_from', '>=', datetime(year, 1, 1)),
                ('date_from', '<', datetime(year + 1, 1, 1)),
            ]
            if leave_id:
                domain.append(('id', '!=', leave_id))

            total_taken = sum(self.sudo().search(domain).mapped('number_of_days'))

            today = fields.Date.today()
            details = self.env['hr.leave.allocation']._compute_employee_entitlement(
                leave.employee_id, date(year, 12, 31),
            )
            schedule = self.env['hr.leave.allocation']._annual_accrual_schedule(leave.employee_id, year, details)
            start_month = schedule['first_eligible_month']
            months_elapsed = max(0, today.month - start_month + 1) if start_month else 0
            annual_entitlement = details['total_annual']
            monthly_rate = schedule['monthly_rate']
            accrued_balance = min(monthly_rate * months_elapsed, total_allocated)
            available = max(0, accrued_balance - total_taken)

            requested = leave.number_of_days or 0
            if requested > available and not leave.accrual_limit_override:
                raise ValidationError(_(
                    "Monthly Accrual Limit Exceeded!\n\n"
                    "%(employee)s cannot take %(requested).2f day(s) of %(leave_type)s.\n\n"
                    "• Monthly accrual rate: %(rate).2f days/month (annual entitlement ÷ 12)\n"
                    "• Annual entitlement: %(annual).2f days\n"
                    "• Months elapsed (from %(start_month)s): %(months)d\n"
                    "• Accrued balance: %(accrued).2f days\n"
                    "• Already taken/pending: %(taken).2f days\n"
                    "• Available: %(available).2f days",
                    employee=leave.employee_id.name,
                    requested=requested,
                    leave_type=leave_type.name,
                     rate=round(monthly_rate, 2),
                     annual=round(annual_entitlement, 2),
                     start_month=(
                         date(year, start_month, 1).strftime('%B %Y')
                         if start_month else _('not eligible in this year')
                     ),
                     months=months_elapsed,
                     accrued=round(accrued_balance, 2),
                     taken=round(total_taken, 2),
                     available=round(available, 2),
                ))

            _logger.info(
                "Monthly accrual check passed for %s: %.2f requested, %.2f available, %.2f rate",
                leave.employee_id.name, requested, available, monthly_rate,
            )
