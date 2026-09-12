# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hire_date = fields.Datetime(string='Hire Date')
    admin_type = fields.Selection([
        ('admin_indirect', 'اداري غير مباشر'),
        ('admin_direct', 'اداري مباشر'),
        ('production_indirect', 'انتاجي غير مباشر'),
        ('production_direct', 'انتاجي مباشر'),
    ], string='Administrative Type')


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    hire_date = fields.Datetime(string='Hire Date', readonly=True)
    admin_type = fields.Selection([
        ('admin_indirect', 'اداري غير مباشر'),
        ('admin_direct', 'اداري مباشر'),
        ('production_indirect', 'انتاجي غير مباشر'),
        ('production_direct', 'انتاجي مباشر'),
    ], string='Administrative Type', readonly=True)
