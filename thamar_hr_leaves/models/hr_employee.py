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
    has_verified_service_bonus = fields.Boolean(
        string='استحقاق زيادة مدة الخدمة مثبت', tracking=True,
        help='استحقاق 9 أيام موثق ببيانات الموارد البشرية عند عدم توفر عدد سنوات التأمين. لا يجمع مع زيادة العمر.',
    )
    leave_opening_balance_ids = fields.One2many('hr.leave.opening.balance', 'employee_id')
    leave_balance_cutoff_date = fields.Date(string='تاريخ رصيد الشيت', compute='_compute_opening_balance_summary')
    leave_carryover_balance = fields.Float(string='الرصيد المرحّل من السنة السابقة', compute='_compute_opening_balance_summary')
    leave_source_year_entitlement = fields.Float(string='استحقاق السنة شامل المؤثرات', compute='_compute_opening_balance_summary')
    leave_source_gross_balance = fields.Float(string='إجمالي الرصيد قبل الإجازات', compute='_compute_opening_balance_summary')
    leave_source_used_balance = fields.Float(string='المستخدم حتى تاريخ الشيت', compute='_compute_opening_balance_summary')
    leave_source_remaining_balance = fields.Float(string='المتبقي حسب الشيت', compute='_compute_opening_balance_summary')
    leave_source_annual_balance = fields.Float(string='الاعتيادي حسب الشيت', compute='_compute_opening_balance_summary')
    leave_source_casual_balance = fields.Float(string='العارض حسب الشيت', compute='_compute_opening_balance_summary')
    leave_current_annual_balance = fields.Float(string='المتبقي الاعتيادي للسنة', compute='_compute_opening_balance_summary')
    leave_current_casual_balance = fields.Float(string='المتبقي العارض للسنة', compute='_compute_opening_balance_summary')
    leave_current_total_balance = fields.Float(string='إجمالي المتبقي للسنة', compute='_compute_opening_balance_summary')

    def _compute_opening_balance_summary(self):
        today = fields.Date.today()
        for employee in self:
            balances = employee.leave_opening_balance_ids.filtered(
                lambda b: b.balance_year == today.year and b.balance_basis == 'year_remaining'
            )
            employee.leave_balance_cutoff_date = max(balances.mapped('balance_date'), default=False)
            employee.leave_carryover_balance = sum(balances.mapped('carryover_days'))
            employee.leave_source_year_entitlement = sum(balances.mapped('year_entitlement_days'))
            employee.leave_source_gross_balance = sum(balances.mapped('gross_balance_days'))
            employee.leave_source_used_balance = sum(balances.mapped('used_before_cutoff_days'))
            employee.leave_source_remaining_balance = sum(balances.mapped('amount'))
            employee.leave_source_annual_balance = sum(balances.filtered('leave_type_id.is_annual_leave').mapped('amount'))
            employee.leave_source_casual_balance = sum(balances.filtered('leave_type_id.is_casual_leave').mapped('amount'))
            annual = casual = 0.0
            for balance in balances:
                status = employee._get_monthly_accrual_status(balance.leave_type_id, today.year, today)
                if balance.leave_type_id.is_annual_leave:
                    annual += status['remaining_balance']
                else:
                    casual += status['remaining_balance']
            employee.leave_current_annual_balance = annual
            employee.leave_current_casual_balance = casual
            employee.leave_current_total_balance = annual + casual

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
    leave_casual_monthly_rate = fields.Float(
        string='معدل الاستحقاق الشهري للعارضة',
        compute='_compute_accrual_status',
        help='رصيد الإجازة العارضة السنوي مقسوماً على 12.',
    )
    leave_casual_months_accrued = fields.Integer(
        string='عدد أشهر الاستحقاق للعارضة',
        compute='_compute_accrual_status',
        help='عدد أشهر الاستحقاق المنقضية للإجازة العارضة.',
    )
    leave_casual_accrual_cap = fields.Float(
        string='الحد التراكمي للعارضة حتى الشهر الحالي',
        compute='_compute_accrual_status',
        help='أقصى رصيد عارض يمكن استخدامه حتى الشهر الحالي.',
    )
    leave_casual_accrued_remaining = fields.Float(
        string='الرصيد الشهري المتاح للعارضة',
        compute='_compute_accrual_status',
        help='الحد التراكمي للعارضة بعد خصم الإجازات المأخوذة أو المعلقة.',
    )

    @api.depends('birthday', 'hire_date', 'external_experience_years', 'is_hazardous_location', 'has_verified_service_bonus')
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

    def _get_monthly_accrual_status(self, leave_type, year, today):
        """Return the usable current-year balance for one leave type.

        The same calculation is used by the employee form and the request
        constraint.  Unused monthly amounts remain in ``accrual_cap`` and are
        therefore available in later months of the same calendar year.
        """
        self.ensure_one()
        return self.env['hr.leave.allocation']._get_monthly_accrual_status(
            self, leave_type, year, as_of_date=today,
        )

    def _compute_accrual_status(self):
        """Compute live monthly accrual status for annual and casual leave."""
        today = fields.Date.today()
        year = today.year
        Allocation = self.env['hr.leave.allocation'].sudo()
        annual_type_cache = {}
        casual_type_cache = {}

        for emp in self:
            company_id = emp.company_id.id if emp.company_id else False
            if company_id not in annual_type_cache:
                annual_type_cache[company_id] = Allocation._get_annual_leave_type(emp.company_id)
            if company_id not in casual_type_cache:
                casual_type_cache[company_id] = Allocation._get_casual_leave_type(emp.company_id)

            annual_status = emp._get_monthly_accrual_status(
                annual_type_cache[company_id], year, today,
            )
            casual_status = emp._get_monthly_accrual_status(
                casual_type_cache[company_id], year, today,
            )
            emp.leave_annual_monthly_rate = annual_status['monthly_rate']
            emp.leave_annual_months_accrued = annual_status['months_accrued']
            emp.leave_annual_accrual_cap = annual_status['accrual_cap']
            emp.leave_annual_accrued_remaining = annual_status['accrued_remaining']
            emp.leave_casual_monthly_rate = casual_status['monthly_rate']
            emp.leave_casual_months_accrued = casual_status['months_accrued']
            emp.leave_casual_accrual_cap = casual_status['accrual_cap']
            emp.leave_casual_accrued_remaining = casual_status['accrued_remaining']

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

    def action_open_leave_opening_balances(self):
        """Open the safe mid-year balance entry screen for this employee."""
        self.ensure_one()
        return {
            'name': _('Opening Leave Balances'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.opening.balance',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    has_verified_service_bonus = fields.Boolean(related='employee_id.has_verified_service_bonus')

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
    leave_annual_monthly_rate = fields.Float(
        string='Annual Monthly Accrual Rate',
        related='employee_id.leave_annual_monthly_rate',
    )
    leave_annual_months_accrued = fields.Integer(
        string='Annual Months Accrued',
        related='employee_id.leave_annual_months_accrued',
    )
    leave_annual_accrual_cap = fields.Float(
        string='Annual Accrued Balance',
        related='employee_id.leave_annual_accrual_cap',
    )
    leave_annual_accrued_remaining = fields.Float(
        string='Annual Available Balance',
        related='employee_id.leave_annual_accrued_remaining',
    )
    leave_casual_monthly_rate = fields.Float(
        string='Casual Monthly Accrual Rate',
        related='employee_id.leave_casual_monthly_rate',
    )
    leave_casual_months_accrued = fields.Integer(
        string='Casual Months Accrued',
        related='employee_id.leave_casual_months_accrued',
    )
    leave_casual_accrual_cap = fields.Float(
        string='Casual Accrued Balance',
        related='employee_id.leave_casual_accrual_cap',
    )
    leave_casual_accrued_remaining = fields.Float(
        string='Casual Available Balance',
        related='employee_id.leave_casual_accrued_remaining',
    )
