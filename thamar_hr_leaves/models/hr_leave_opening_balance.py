# -*- coding: utf-8 -*-
"""Opening balances for a safe mid-year Time Off rollout."""

from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrLeaveOpeningBalance(models.Model):
    _name = 'hr.leave.opening.balance'
    _description = 'Leave Opening Balance'
    _order = 'balance_year desc, employee_id, leave_type_id'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade', index=True,
    )
    leave_type_id = fields.Many2one(
        'hr.leave.type', string='Leave Type', required=True, ondelete='restrict', index=True,
        domain="['|', ('is_annual_leave', '=', True), ('is_casual_leave', '=', True)]",
    )
    balance_date = fields.Date(
        string='Balance Cut-off Date', required=True, index=True,
        help=(
            'The entered balance is the employee\'s actual remaining balance '
            'on this exact date. Any later monthly entitlement is added from '
            'the first day of the following calendar month.'
        ),
    )
    balance_year = fields.Integer(string='Leave Year', required=True, readonly=True, index=True)
    amount = fields.Float(
        string='Remaining Opening Balance (Days)', required=True,
        help=(
            'Actual remaining balance on the cut-off date. A negative value '
            'is allowed and represents leave already taken in advance.'
        ),
    )
    balance_basis = fields.Selection([
        ('accrued', 'رصيد مستحق حتى تاريخ القطع'),
        ('year_remaining', 'المتبقي من رصيد السنة بعد الإجازات'),
    ], required=True, default='accrued', string='أساس الرصيد',
        help='رصيد السنة يشمل الاستحقاقات المستقبلية؛ يفتح الحد الشهري داخل هذا الرصيد دون إضافتها إليه مرة أخرى.')
    carryover_days = fields.Float(
        string='الرصيد المرحّل من السنة السابقة',
        help='مكوّن من رصيد السنة المستورد، وليس إضافة جديدة إلى المتبقي.',
    )
    year_entitlement_days = fields.Float(
        string='استحقاق السنة شامل المؤثرات',
        help='استحقاق هذا النوع في سنة الرصيد، بعد نسبة سنة التعيين، دون الرصيد المرحّل.',
    )
    service_bonus_days = fields.Float(
        string='زيادة مدة الخدمة أو العمر (أيام)',
        help='زيادة إجازة واردة في المصدر، وليست سنوات خبرة تأمينية.',
    )
    hazard_bonus_days = fields.Float(string='زيادة الوظائف الفنية (أيام)')
    gross_balance_days = fields.Float(
        string='إجمالي الرصيد قبل الإجازات', compute='_compute_source_totals',
    )
    used_before_cutoff_days = fields.Float(
        string='المستخدم قبل تاريخ القطع', compute='_compute_source_totals',
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(related='employee_id.company_id', store=True, readonly=True)
    opening_allocation_ids = fields.One2many(
        'hr.leave.allocation', 'opening_balance_id',
        string='Opening Balance Adjustments', readonly=True,
    )

    @api.depends('carryover_days', 'year_entitlement_days', 'amount')
    def _compute_source_totals(self):
        for balance in self:
            balance.gross_balance_days = balance.carryover_days + balance.year_entitlement_days
            balance.used_before_cutoff_days = balance.gross_balance_days - balance.amount

    def _get_source_monthly_rate(self):
        self.ensure_one()
        policy = self.env['hr.leave.allocation']._get_monthly_accrual_policy(
            self.employee_id, self.leave_type_id, self.balance_year,
        )
        months = policy['eligible_months'] if policy else 0
        return self.year_entitlement_days / months if months else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for values in vals_list:
            values = dict(values)
            if values.get('balance_date'):
                balance_date = fields.Date.to_date(values['balance_date'])
                values['balance_date'] = balance_date
                values['balance_year'] = balance_date.year
            prepared_vals_list.append(values)

        balances = super().create(prepared_vals_list)
        for balance in balances:
            if not balance.employee_id.hire_date:
                raise ValidationError(_(
                    'Set the employee Hire Date before recording an opening leave balance.'
                ))
            # This only creates a missing standard allocation.  Existing
            # allocations are preserved and never overwritten by the rollout.
            if balance.balance_basis == 'accrued':
                self.env['hr.leave.allocation']._generate_employee_allocations(
                    balance.employee_id, balance.balance_year,
                )
            balance._sync_opening_allocation_adjustment()
        return balances

    def write(self, values):
        values = dict(values)
        if values.get('balance_date'):
            balance_date = fields.Date.to_date(values['balance_date'])
            values['balance_date'] = balance_date
            values['balance_year'] = balance_date.year
        result = super().write(values)
        if {'employee_id', 'leave_type_id', 'balance_date', 'amount', 'balance_basis',
                'year_entitlement_days'} & values.keys():
            for balance in self:
                if not balance.employee_id.hire_date:
                    raise ValidationError(_(
                        'Set the employee Hire Date before recording an opening leave balance.'
                    ))
                if balance.balance_basis == 'accrued':
                    self.env['hr.leave.allocation']._generate_employee_allocations(
                        balance.employee_id, balance.balance_year,
                    )
                balance._sync_opening_allocation_adjustment()
        return result

    def _sync_opening_allocation_adjustment(self):
        """Keep Odoo's native available-balance checks aligned with the source balance.

        The monthly constraint remains the functional source of truth.  This
        small, traceable allocation only prevents Odoo from rejecting a valid
        carried balance because it is larger than the current legal annual
        entitlement.  It is never an extra leave-policy entitlement.
        """
        Allocation = self.env['hr.leave.allocation'].sudo()
        for balance in self:
            if balance.balance_basis == 'year_remaining':
                balance._sync_year_remaining_allocation()
                continue
            adjustments = balance.opening_allocation_ids.sudo()
            if adjustments:
                adjustments.with_context(allocation_skip_state_check=True).unlink()

            details = Allocation._compute_employee_entitlement(
                balance.employee_id, date(balance.balance_year, 12, 31),
            )
            policy = Allocation._get_monthly_accrual_policy(
                balance.employee_id, balance.leave_type_id, balance.balance_year, details,
            )
            if not policy:
                continue

            # The source balance is measured on the cut-off date.  Only whole
            # later calendar months accrue under the monthly policy.
            months_after_cutoff = max(0, 12 - balance.balance_date.month)
            required_total = max(
                0.0,
                balance.amount + policy['monthly_rate'] * months_after_cutoff,
            )
            existing_total = sum(Allocation.search([
                ('employee_id', '=', balance.employee_id.id),
                ('holiday_status_id', '=', balance.leave_type_id.id),
                ('state', '=', 'validate'),
                ('leave_year', '=', balance.balance_year),
                ('is_opening_balance_adjustment', '=', False),
            ]).mapped('number_of_days'))
            adjustment_days = round(max(0.0, required_total - existing_total), 2)
            if not adjustment_days:
                continue

            adjustment = Allocation.create({
                'employee_id': balance.employee_id.id,
                'holiday_status_id': balance.leave_type_id.id,
                'number_of_days': adjustment_days,
                'date_from': balance.balance_date,
                'date_to': date(balance.balance_year, 12, 31)
                if balance.leave_type_id.is_casual_leave else False,
                'notes': _(
                    'Technical opening-balance adjustment. Source balance: '
                    '%(amount).2f days on %(balance_date)s.',
                    amount=balance.amount,
                    balance_date=balance.balance_date.isoformat(),
                ),
                'allocation_type': 'regular',
                'leave_year': balance.balance_year,
                'is_opening_balance_adjustment': True,
                'opening_balance_id': balance.id,
            })
            # Opening-balance adjustments are system records, not allocation
            # requests awaiting a manager.  Make them immediately available.
            if adjustment.state == 'confirm':
                adjustment._action_validate()

    def _sync_year_remaining_allocation(self):
        """Replace full-year availability with the verified net snapshot.

        Preserve the historical policy allocations, ending their validity the
        day before the cut-off. Reuse the linked snapshot allocation in place;
        never delete/recreate its chatter or add the yearly policy twice.
        """
        Allocation = self.env['hr.leave.allocation'].sudo()
        for balance in self:
            policy_allocations = Allocation.search([
                ('employee_id', '=', balance.employee_id.id),
                ('holiday_status_id', '=', balance.leave_type_id.id),
                ('leave_year', '=', balance.balance_year),
                ('is_auto_generated', '=', True),
                ('opening_balance_id', '=', False),
                ('state', '!=', 'refuse'),
            ])
            for allocation in policy_allocations:
                if allocation.date_from >= balance.balance_date:
                    allocation.action_refuse()
                elif not allocation.date_to or allocation.date_to >= balance.balance_date:
                    allocation.write({'date_to': balance.balance_date - timedelta(days=1)})

            linked = balance.opening_allocation_ids.sudo().sorted('id')
            extras = linked[1:].filtered(lambda a: a.state != 'refuse')
            if extras:
                extras.action_refuse()
            if balance.amount <= 0:
                active = linked[:1].filtered(lambda a: a.state != 'refuse')
                if active:
                    active.action_refuse()
                continue

            values = {
                'employee_id': balance.employee_id.id,
                'holiday_status_id': balance.leave_type_id.id,
                'number_of_days': balance.amount,
                'date_from': balance.balance_date,
                'date_to': date(balance.balance_year, 12, 31),
                'notes': _('Verified remaining yearly balance on %(date)s. '
                           'Carryover and entitlement bonuses are already included.',
                           date=balance.balance_date),
                'allocation_type': 'regular',
                'leave_year': balance.balance_year,
                'is_opening_balance_adjustment': True,
                'opening_balance_id': balance.id,
            }
            if linked:
                allocation = linked[:1]
                allocation.write(values)
            else:
                allocation = Allocation.create(values)
            if allocation.state != 'validate':
                allocation._action_validate()

    @api.constrains('employee_id', 'leave_type_id', 'balance_year')
    def _check_single_opening_balance_per_year(self):
        for balance in self:
            duplicate = self.sudo().search([
                ('employee_id', '=', balance.employee_id.id),
                ('leave_type_id', '=', balance.leave_type_id.id),
                ('balance_year', '=', balance.balance_year),
                ('id', '!=', balance.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'Only one opening balance is allowed for the same employee, leave type, and year. Edit the existing balance to correct it.'
                ))

    @api.constrains('amount', 'leave_type_id')
    def _check_opening_balance(self):
        for balance in self:
            if balance.leave_type_id and not (
                balance.leave_type_id.is_annual_leave
                or balance.leave_type_id.is_casual_leave
            ):
                raise ValidationError(_(
                    'Opening balances are supported only for Annual Leave and Casual Leave.'
                ))
