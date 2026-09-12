# -*- coding: utf-8 -*-

from odoo import api, fields, models


class TransportRoute(models.Model):
    _name = 'transport.route'
    _description = 'Transportation Route'
    _order = 'code, name'

    name = fields.Char(string='اسم خط السير', required=True, translate=True)
    code = fields.Char(string='كود خط السير', required=True, copy=False, index=True)
    vehicle_ids = fields.One2many('transport.vehicle', 'route_id', string='المركبات')
    station_ids = fields.One2many('transport.station', 'route_id', string='المحطات')
    employee_ids = fields.One2many('hr.employee', 'transport_route_id', string='الموظفون')
    total_capacity = fields.Integer(string='إجمالي السعة اليومية', compute='_compute_capacity_statistics', store=True)
    total_assigned = fields.Integer(string='إجمالي الموظفين المسكنين', compute='_compute_capacity_statistics', store=True)
    total_remaining_seats = fields.Integer(string='إجمالي المقاعد الشاغرة', compute='_compute_capacity_statistics', store=True)

    _sql_constraints = [
        ('transport_route_code_unique', 'unique(code)', 'يجب أن يكون كود خط السير فريداً.'),
    ]

    @api.depends('vehicle_ids.effective_capacity', 'employee_ids')
    def _compute_capacity_statistics(self):
        for route in self:
            route.total_capacity = sum(route.vehicle_ids.mapped('effective_capacity'))
            route.total_assigned = len(route.employee_ids)
            route.total_remaining_seats = route.total_capacity - route.total_assigned
