# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    _THAMAR_PORTAL_LEAVE_TYPE_XMLIDS = (
        'thamar_hr_leaves.leave_type_annual',
        'thamar_hr_leaves.leave_type_casual',
        'thamar_hr_leaves.leave_type_work_injury',
        'thamar_hr_leaves.leave_type_sick',
        'thamar_hr_leaves.leave_type_unpaid',
        'thamar_hr_leaves.leave_type_marriage_paid',
        'thamar_hr_leaves.leave_type_death_paid',
        'thamar_hr_leaves.leave_type_newborn_paid',
        'thamar_hr_leaves.leave_type_exams',
    )

    requires_clinical_approval = fields.Boolean(string='Requires Clinical Approval', default=False, help="If checked, leaves of this type will require approval from the company's Clinical Manager.")

    manager_only_requests = fields.Boolean(
        string='Manager Creates Requests',
        default=False,
        help=(
            'Employees cannot create, edit, or delete requests of this type '
            'from the employee portal. Their manager or a Time Off officer '
            'must create the request from the internal Time Off application.'
        ),
    )
    portal_self_service = fields.Boolean(
        string='Available in Employee Portal',
        default=False,
        help=(
            'Allow employees to select this time off type when creating a '
            'request from the portal. Manager-only types remain unavailable.'
        ),
    )

    @api.model
    def _configure_thamar_portal_leave_types(self):
        """Keep the portal whitelist stable across installs and upgrades."""
        leave_types = self.browse([
            record.id
            for xmlid in self._THAMAR_PORTAL_LEAVE_TYPE_XMLIDS
            if (record := self.env.ref(xmlid, raise_if_not_found=False))
        ])
        leave_types.write({'portal_self_service': True})

    is_annual_leave = fields.Boolean(
        string='Is Annual Leave (إجازة اعتيادية)',
        default=False,
        help="Mark this leave type as the Annual Leave type. "
             "Used by the auto-allocation system to identify the correct leave type.",
    )
    is_casual_leave = fields.Boolean(
        string='Is Casual Leave (إجازة عارضة)',
        default=False,
        help="Mark this leave type as the Casual Leave type. "
             "Used by the auto-allocation system to identify the correct leave type.",
    )
    use_monthly_accrual = fields.Boolean(
        string='Monthly Accrual Policy (سياسة الاستحقاق الشهري)',
        default=False,
        help="If enabled, the annual leave balance accrues monthly at "
             "(Total Days / 12) per month. Employees cannot take more "
             "than their accrued balance up to the leave request month. "
             "Unused accrued days roll over automatically within the year.",
    )
    split_day_night = fields.Boolean(
        string='Split Day/Night Overtime',
        default=False,
        help='When enabled, work entries created from this leave type '
             'will have their duration split into Day Hours (6 AM – 9 PM) '
             'and Night Hours (9 PM – 6 AM) for overtime payroll calculation.',
    )
    day_start_hour = fields.Float(
        string='Day Start Hour',
        default=6.0,
        help='Hour when day shift starts (0-24)',
    )
    day_end_hour = fields.Float(
        string='Day End Hour',
        default=21.0,
        help='Hour when day shift ends (0-24)',
    )

    @api.constrains('is_annual_leave')
    def _check_single_annual_leave(self):
        """Ensure only one leave type is marked as Annual Leave per company."""
        for leave_type in self:
            if leave_type.is_annual_leave:
                domain = [
                    ('is_annual_leave', '=', True),
                    ('id', '!=', leave_type.id),
                ]
                if leave_type.company_id:
                    domain.append(('company_id', '=', leave_type.company_id.id))
                else:
                    domain.append(('company_id', '=', False))
                existing = self.search_count(domain)
                if existing:
                    raise ValidationError(_(
                        "Only one leave type can be marked as Annual Leave per company."
                    ))

    @api.constrains('is_casual_leave')
    def _check_single_casual_leave(self):
        """Ensure only one leave type is marked as Casual Leave per company."""
        for leave_type in self:
            if leave_type.is_casual_leave:
                domain = [
                    ('is_casual_leave', '=', True),
                    ('id', '!=', leave_type.id),
                ]
                if leave_type.company_id:
                    domain.append(('company_id', '=', leave_type.company_id.id))
                else:
                    domain.append(('company_id', '=', False))
                existing = self.search_count(domain)
                if existing:
                    raise ValidationError(_(
                        "Only one leave type can be marked as Casual Leave per company."
                    ))
