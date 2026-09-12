# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ── Custom input fields ──
    external_experience_years = fields.Float(
        string='سنوات الخبرة التأمينية الخارجية',
        default=0.0,
        help='سنوات الخبرة التأمينية السابقة التي تدخل في احتساب إجمالي مدة الخدمة.',
        tracking=True,
    )
    is_hazardous_location = fields.Boolean(
        string='وظائف فنية',
        default=False,
        help='يمنح الموظف 7 أيام إضافية في رصيد الإجازة الاعتيادية.',
        tracking=True,
    )

    # ── Computed entitlement detail fields (readonly, for transparency) ──
    leave_employee_age = fields.Integer(
        string='عمر الموظف',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='يُحسب من تاريخ الميلاد.',
    )
    leave_current_service_years = fields.Float(
        string='سنوات الخدمة الحالية',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='سنوات الخدمة في الشركة بناءً على تاريخ التعيين.',
    )
    leave_total_service_years = fields.Float(
        string='إجمالي سنوات الخدمة',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='سنوات الخدمة الحالية مضافاً إليها سنوات الخبرة التأمينية الخارجية.',
    )
    leave_base_annual_days = fields.Float(
        string='الرصيد الأساسي للإجازة الاعتيادية',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='8 أيام في سنة التعيين، ثم 14 يوماً في كل سنة تالية.',
    )
    leave_age_bonus = fields.Float(
        string='زيادة السن فوق 50 سنة',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='9 أيام إضافية لمن تجاوز 50 سنة، ولا تُجمع مع زيادة خبرة 10 سنوات.',
    )
    leave_experience_bonus = fields.Float(
        string='زيادة خبرة 10 سنوات فأكثر',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='9 أيام إضافية عند بلوغ إجمالي الخدمة 10 سنوات، ولا تُجمع مع زيادة السن.',
    )
    leave_hazardous_bonus = fields.Float(
        string='زيادة الوظائف الفنية',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='7 أيام إضافية للموظف في وظيفة فنية.',
    )
    leave_total_annual_entitlement = fields.Float(
        string='إجمالي رصيد الإجازة الاعتيادية',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='مجموع الرصيد الأساسي وزيادات السن أو الخبرة والوظائف الفنية.',
    )
    leave_casual_entitlement = fields.Float(
        string='رصيد الإجازة العارضة',
        compute='_compute_leave_entitlement_details',
        store=True,
        help='7 أيام سنوياً، وتُحسب بنسبة الأشهر المؤهلة المتبقية في سنة التعيين.',
    )

    # ── Monthly Accrual Status (live, non-stored) ──
    leave_annual_monthly_rate = fields.Float(
        string='معدل الاستحقاق الشهري',
        compute='_compute_accrual_status',
        help='إجمالي الرصيد الاعتيادي مقسوماً على 12.',
    )
    leave_annual_months_accrued = fields.Integer(
        string='عدد الأشهر المستحقة',
        compute='_compute_accrual_status',
        help='عدد أشهر الاستحقاق المنقضية من الشهر التالي للتعيين أو من يناير.',
    )
    leave_annual_accrual_cap = fields.Float(
        string='الحد التراكمي حتى الشهر الحالي',
        compute='_compute_accrual_status',
        help='أقصى رصيد اعتيادي يمكن استخدامه حتى الشهر الحالي.',
    )
    leave_annual_accrued_remaining = fields.Float(
        string='الرصيد الشهري المتاح',
        compute='_compute_accrual_status',
        help='الحد التراكمي بعد خصم الإجازات المأخوذة أو المعلقة.',
    )

    @api.depends('birthday', 'hire_date', 'external_experience_years', 'is_hazardous_location')
    def _compute_leave_entitlement_details(self):
        """Compute all leave entitlement breakdown fields for transparency."""
        today = fields.Date.today()
        for emp in self:
            details = self.env['hr.leave.allocation']._compute_employee_entitlement(emp, today)
            emp.leave_employee_age = details['age']
            emp.leave_current_service_years = details['current_service_years']
            emp.leave_total_service_years = details['total_service_years']
            emp.leave_base_annual_days = details['base_days']
            emp.leave_age_bonus = details['age_bonus']
            emp.leave_experience_bonus = details['experience_bonus']
            emp.leave_hazardous_bonus = details['hazardous_bonus']
            emp.leave_total_annual_entitlement = details['total_annual']
            casual_schedule = self.env['hr.leave.allocation']._casual_allocation_schedule(
                emp, today.year, details,
            )
            emp.leave_casual_entitlement = casual_schedule['new_entitlement']

    def _compute_accrual_status(self):
        """Compute the live monthly accrual status for annual leave."""
        today = fields.Date.today()
        year = today.year
        month = today.month

        Allocation = self.env['hr.leave.allocation'].sudo()
        Leave = self.env['hr.leave'].sudo()
        annual_type_cache = {}

        for emp in self:
            # Default values
            emp.leave_annual_monthly_rate = 0.0
            emp.leave_annual_months_accrued = 0
            emp.leave_annual_accrual_cap = 0.0
            emp.leave_annual_accrued_remaining = 0.0

            # Find the annual leave type for this employee's company
            company_id = emp.company_id.id if emp.company_id else False
            if company_id not in annual_type_cache:
                annual_type_cache[company_id] = Allocation._get_annual_leave_type(emp.company_id)
            annual_type = annual_type_cache[company_id]

            if not annual_type or not annual_type.use_monthly_accrual:
                continue

            # Total allocation for this year
            allocations = Allocation.search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', annual_type.id),
                ('state', '=', 'validate'),
                ('leave_year', '=', year),
            ])
            total_allocated = sum(allocations.mapped('number_of_days'))
            if not total_allocated:
                continue

            details = Allocation._compute_employee_entitlement(emp, today)
            schedule = Allocation._annual_accrual_schedule(emp, year, details)
            monthly_rate = schedule['monthly_rate']

            # No annual leave accrues in the hire month.
            start_month = schedule['first_eligible_month']
            months_accrued = max(0, month - start_month + 1) if start_month else 0
            accrual_cap = min(round(monthly_rate * months_accrued, 2), total_allocated)

            # Leaves taken/pending this year
            from datetime import datetime as dt
            existing_leaves = Leave.search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', annual_type.id),
                ('state', 'not in', ('refuse', 'cancel')),
                ('date_from', '>=', dt(year, 1, 1)),
                ('date_from', '<', dt(year + 1, 1, 1)),
            ])
            total_taken = sum(existing_leaves.mapped('number_of_days'))

            emp.leave_annual_monthly_rate = round(monthly_rate, 2)
            emp.leave_annual_months_accrued = months_accrued
            emp.leave_annual_accrual_cap = accrual_cap
            emp.leave_annual_accrued_remaining = round(max(0.0, accrual_cap - total_taken), 2)

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate leave allocations when a new employee is created."""
        employees = super().create(vals_list)
        for employee in employees:
            try:
                self.env['hr.leave.allocation']._generate_employee_allocations(employee)
            except Exception as e:
                _logger.warning(
                    "Failed to auto-generate leave allocations for employee %s (ID: %s): %s",
                    employee.name, employee.id, e,
                )
        return employees

    def write(self, vals):
        """Generate missing current-year allocations when Hire Date is set later."""
        result = super().write(vals)
        if 'hire_date' in vals:
            for employee in self.filtered('hire_date'):
                try:
                    self.env['hr.leave.allocation']._generate_employee_allocations(employee)
                except Exception as error:
                    _logger.warning(
                        "Failed to auto-generate leave allocations after setting Hire Date for %s (ID: %s): %s",
                        employee.name, employee.id, error,
                    )
        return result

    def action_regenerate_leave_allocations(self):
        """Manual button action to regenerate leave allocations for the current year."""
        for employee in self:
            self.env['hr.leave.allocation']._generate_employee_allocations(employee)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Leave Allocations"),
                'message': _("Leave allocations have been regenerated successfully."),
                'type': 'success',
                'sticky': False,
            },
        }


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # Mirror input fields as related (readonly by nature on public model)
    external_experience_years = fields.Float(
        string='External Insured Experience (Years)',
        related='employee_id.external_experience_years',
        readonly=True,
    )
    is_hazardous_location = fields.Boolean(
        string='Hazardous / Remote Location',
        related='employee_id.is_hazardous_location',
        readonly=True,
    )

    # Mirror computed fields as related from the real employee
    leave_employee_age = fields.Integer(
        string='Employee Age',
        related='employee_id.leave_employee_age',
    )
    leave_current_service_years = fields.Float(
        string='Current Service Years',
        related='employee_id.leave_current_service_years',
    )
    leave_total_service_years = fields.Float(
        string='Total Service Years',
        related='employee_id.leave_total_service_years',
    )
    leave_base_annual_days = fields.Float(
        string='Base Annual Days',
        related='employee_id.leave_base_annual_days',
    )
    leave_age_bonus = fields.Float(
        string='Over-50 Age Bonus',
        related='employee_id.leave_age_bonus',
    )
    leave_experience_bonus = fields.Float(
        string='10+ Years Experience Bonus',
        related='employee_id.leave_experience_bonus',
    )
    leave_hazardous_bonus = fields.Float(
        string='Hazardous Location Bonus',
        related='employee_id.leave_hazardous_bonus',
    )
    leave_total_annual_entitlement = fields.Float(
        string='Total Annual Entitlement',
        related='employee_id.leave_total_annual_entitlement',
    )
    leave_casual_entitlement = fields.Float(
        string='Casual Leave Entitlement',
        related='employee_id.leave_casual_entitlement',
    )
