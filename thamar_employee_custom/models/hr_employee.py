# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Payroll custom fields
    x_previous_wage = fields.Float(
        string='Previous Wage',
        help='Employee previous wage amount'
    )
    x_promotion_amount = fields.Float(
        string='Promotion Amount',
        help='Promotion amount for the employee'
    )
    x_increase_rate = fields.Float(
        string='Increase Rate',
        help='Salary increase rate percentage'
    )
    x_fixed_allowances = fields.Float(
        string='Fixed Allowances',
        help='Fixed allowances amount'
    )
    x_tax_personal_exemption = fields.Float(
        string='Tax Personal Exemption',
        help='الإعفاء الشخصي السنوي - Annual personal tax exemption'
    )
    x_tax_family_exemption = fields.Float(
        string='Tax Family Exemption',
        help='الإعفاءات العائلية السنوية - Annual family tax exemptions'
    )

