# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransportVehicle(models.Model):
    _name = 'transport.vehicle'
    _description = 'Transportation Vehicle'
    _order = 'route_id, plate_number'

    name = fields.Char(string='المركبة', compute='_compute_name', store=True, readonly=False)
    plate_number = fields.Char(string='رقم اللوحة / كود المركبة', required=True, copy=False, index=True)
    route_id = fields.Many2one('transport.route', string='خط السير', required=True, ondelete='cascade', index=True)
    driver_name = fields.Char(string='اسم السائق')
    driver_phone = fields.Char(string='هاتف السائق')
    standard_capacity = fields.Integer(string='السعة القياسية', default=14, required=True)
    active_shifts = fields.Selection(
        [('1', 'وردية واحدة'), ('2', 'ورديتان'), ('3', '3 ورديات')],
        string='عدد الورديات النشطة',
        default='1', required=True,
    )
    effective_capacity = fields.Integer(string='السعة الفعلية اليومية', compute='_compute_capacity', store=True)
    passenger_ids = fields.One2many('hr.employee', 'transport_vehicle_id', string='الركاب')
    station_schedule_ids = fields.One2many('transport.vehicle.station', 'vehicle_id', string='جدول المحطات')
    shift_one_schedule_ids = fields.One2many(
        'transport.vehicle.station', 'vehicle_id', string='مواعيد الوردية الأولى',
        domain=[('shift_number', '=', '1')],
    )
    shift_two_schedule_ids = fields.One2many(
        'transport.vehicle.station', 'vehicle_id', string='مواعيد الوردية الثانية',
        domain=[('shift_number', '=', '2')],
    )
    shift_three_schedule_ids = fields.One2many(
        'transport.vehicle.station', 'vehicle_id', string='مواعيد الوردية الثالثة',
        domain=[('shift_number', '=', '3')],
    )
    occupied_seats = fields.Integer(string='المقاعد المشغولة', compute='_compute_capacity', store=True)
    remaining_seats = fields.Integer(string='المقاعد الشاغرة', compute='_compute_capacity', store=True)
    occupancy_rate = fields.Float(string='نسبة الإشغال', compute='_compute_capacity', store=True, digits=(5, 2))

    _sql_constraints = [
        ('transport_vehicle_plate_unique', 'unique(plate_number)', 'يجب أن يكون رقم اللوحة فريداً.'),
    ]

    @api.depends('plate_number')
    def _compute_name(self):
        for vehicle in self:
            vehicle.name = vehicle.plate_number or False

    @api.depends('standard_capacity', 'active_shifts', 'passenger_ids.transport_vehicle_id')
    def _compute_capacity(self):
        for vehicle in self:
            vehicle.effective_capacity = vehicle.standard_capacity * int(vehicle.active_shifts or 0)
            vehicle.occupied_seats = len(vehicle.passenger_ids)
            vehicle.remaining_seats = vehicle.effective_capacity - vehicle.occupied_seats
            vehicle.occupancy_rate = (
                vehicle.occupied_seats / vehicle.effective_capacity * 100
                if vehicle.effective_capacity else 0.0
            )

    @api.constrains('passenger_ids', 'standard_capacity', 'active_shifts')
    def _check_capacity(self):
        for vehicle in self:
            if vehicle.occupied_seats > vehicle.effective_capacity:
                message = _(
                    'المركبة %(vehicle)s مكتملة العدد. عدد الركاب %(occupied)s '
                    'بينما سعتها الفعلية %(capacity)s مقعداً.'
                ) % {
                    'vehicle': vehicle.display_name,
                    'occupied': vehicle.occupied_seats,
                    'capacity': vehicle.effective_capacity,
                }
                raise ValidationError(message)

    @api.constrains('standard_capacity')
    def _check_standard_capacity(self):
        if any(vehicle.standard_capacity <= 0 for vehicle in self):
            raise ValidationError(_('يجب أن تكون السعة القياسية أكبر من صفر.'))

    def action_open_assign_employee_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('إضافة موظفين إلى المركبة'),
            'res_model': 'transport.vehicle.assign.employee.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_vehicle_id': self.id},
        }
