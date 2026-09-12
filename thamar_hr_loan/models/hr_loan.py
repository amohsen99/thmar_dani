# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrLoan(models.Model):
    _name = 'hr.loan'
    _description = 'Employee Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Loan Reference',
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        related='employee_id.job_id',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
    )
    loan_type = fields.Selection(
        [('small', 'Small Loan'), ('long', 'Long Loan')],
        string='Loan Type',
        required=True,
        default='small',
        tracking=True,
    )
    loan_amount = fields.Monetary(
        string='Loan Amount',
        required=True,
        tracking=True,
        currency_field='currency_id',
    )
    installment_count = fields.Integer(
        string='Number of Installments',
        default=1,
        tracking=True,
        help='Number of monthly installments. Set to 1 for small loans.',
    )
    payment_start_date = fields.Date(
        string='Payment Start Date',
        required=True,
        tracking=True,
        help='The date of the first installment deduction.',
    )
    installment_amount = fields.Monetary(
        string='Installment Amount',
        compute='_compute_installment_amount',
        store=True,
        currency_field='currency_id',
    )
    total_paid = fields.Monetary(
        string='Total Paid',
        compute='_compute_total_paid',
        store=True,
        currency_field='currency_id',
    )
    balance = fields.Monetary(
        string='Balance',
        compute='_compute_total_paid',
        store=True,
        currency_field='currency_id',
    )
    installment_ids = fields.One2many(
        'hr.loan.line',
        'loan_id',
        string='Installments',
    )
    reason = fields.Text(
        string='Reason / Notes',
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting_approval', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('confirm', 'Confirmed'),
            ('done', 'Done'),
            ('refused', 'Refused'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
    )
    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.context_today,
        readonly=True,
    )
    manager_approve_date = fields.Date(
        string='Manager Approval Date',
        readonly=True,
        copy=False,
    )
    hr_approve_date = fields.Date(
        string='HR Approval Date',
        readonly=True,
        copy=False,
    )
    manager_id = fields.Many2one(
        'res.users',
        string='Approved by Manager',
        readonly=True,
        copy=False,
    )
    hr_manager_id = fields.Many2one(
        'res.users',
        string='Approved by HR',
        readonly=True,
        copy=False,
    )

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------
    @api.depends('loan_amount', 'installment_count')
    def _compute_installment_amount(self):
        for loan in self:
            if loan.installment_count and loan.installment_count > 0:
                loan.installment_amount = loan.loan_amount / loan.installment_count
            else:
                loan.installment_amount = loan.loan_amount

    @api.depends('installment_ids.paid', 'installment_ids.amount')
    def _compute_total_paid(self):
        for loan in self:
            paid_lines = loan.installment_ids.filtered('paid')
            loan.total_paid = sum(paid_lines.mapped('amount'))
            loan.balance = loan.loan_amount - loan.total_paid

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains('loan_amount')
    def _check_loan_amount(self):
        for loan in self:
            if loan.loan_amount <= 0:
                raise ValidationError(_('Loan amount must be greater than zero.'))

    @api.constrains('installment_count')
    def _check_installment_count(self):
        for loan in self:
            if loan.installment_count <= 0:
                raise ValidationError(
                    _('Number of installments must be at least 1.'))

    @api.constrains('loan_type', 'installment_count')
    def _check_small_loan_installments(self):
        for loan in self:
            if loan.loan_type == 'small' and loan.installment_count != 1:
                raise ValidationError(
                    _('Small loans must have exactly 1 installment.'))

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------
    @api.onchange('loan_type')
    def _onchange_loan_type(self):
        if self.loan_type == 'small':
            self.installment_count = 1

    # -------------------------------------------------------------------------
    # CRUD overrides
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.loan') or _('New')
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Workflow actions
    # -------------------------------------------------------------------------
    def action_submit(self):
        """Draft → Waiting Approval (submit to manager)."""
        for loan in self:
            if loan.state != 'draft':
                raise UserError(
                    _('Only draft loans can be submitted for approval.'))
            if not loan.installment_ids:
                raise UserError(
                    _('Please compute installments before submitting.'))
            loan.write({'state': 'waiting_approval'})

    def action_manager_approve(self):
        """Waiting Approval → Approved (manager approves)."""
        for loan in self:
            if loan.state != 'waiting_approval':
                raise UserError(
                    _('Only loans waiting for approval can be approved.'))
            loan.write({
                'state': 'approved',
                'manager_id': self.env.uid,
                'manager_approve_date': fields.Date.context_today(self),
            })

    def action_hr_approve(self):
        """Approved → Confirmed (HR approves)."""
        for loan in self:
            if loan.state != 'approved':
                raise UserError(
                    _('Only manager-approved loans can be confirmed by HR.'))
            loan.write({
                'state': 'confirm',
                'hr_manager_id': self.env.uid,
                'hr_approve_date': fields.Date.context_today(self),
            })

    def action_refuse(self):
        """Any stage → Refused."""
        for loan in self:
            if loan.state in ('done', 'refused'):
                raise UserError(
                    _('Cannot refuse a loan that is already done or refused.'))
            loan.write({'state': 'refused'})

    def action_reset_draft(self):
        """Refused → Draft."""
        for loan in self:
            if loan.state != 'refused':
                raise UserError(
                    _('Only refused loans can be reset to draft.'))
            loan.write({'state': 'draft'})

    def action_done(self):
        """Mark loan as fully paid."""
        for loan in self:
            loan.write({'state': 'done'})

    # -------------------------------------------------------------------------
    # Installment computation
    # -------------------------------------------------------------------------
    def compute_installments(self):
        """Generate installment lines based on amount, count, and start date."""
        for loan in self:
            if loan.state != 'draft':
                raise UserError(
                    _('Installments can only be computed in draft state.'))
            # Remove existing installment lines
            loan.installment_ids.unlink()

            if not loan.payment_start_date or not loan.loan_amount:
                continue

            installment_amount = loan.loan_amount / loan.installment_count
            remainder = loan.loan_amount - (
                installment_amount * loan.installment_count)

            lines = []
            for i in range(loan.installment_count):
                amount = installment_amount
                # Add any rounding remainder to the last installment
                if i == loan.installment_count - 1:
                    amount += remainder
                lines.append((0, 0, {
                    'date': loan.payment_start_date + relativedelta(months=i),
                    'amount': round(amount, 2),
                    'employee_id': loan.employee_id.id,
                }))
            loan.write({'installment_ids': lines})


class HrLoanLine(models.Model):
    _name = 'hr.loan.line'
    _description = 'Loan Installment Line'
    _order = 'date asc'

    loan_id = fields.Many2one(
        'hr.loan',
        string='Loan',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='loan_id.employee_id',
        store=True,
    )
    date = fields.Date(
        string='Due Date',
        required=True,
    )
    amount = fields.Float(
        string='Amount',
        required=True,
    )
    paid = fields.Boolean(
        string='Paid',
        default=False,
    )
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        readonly=True,
        help='The payslip that deducted this installment.',
    )
