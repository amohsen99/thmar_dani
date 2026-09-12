# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransportStation(models.Model):
    _name = 'transport.station'
    _description = 'Transportation Route Station'
    _order = 'route_id, sequence, id'

    name = fields.Char(string='اسم المحطة', required=True)
    route_id = fields.Many2one('transport.route', string='خط السير', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='الترتيب', default=10)
    notes = fields.Char(string='ملاحظات')
    vehicle_schedule_ids = fields.One2many('transport.vehicle.station', 'station_id', string='مواعيد المركبات')

    _sql_constraints = [
        ('transport_station_route_name_unique', 'unique(route_id, name)', 'اسم المحطة مكرر في خط السير نفسه.'),
    ]


class TransportVehicleStation(models.Model):
    _name = 'transport.vehicle.station'
    _description = 'Vehicle Station Shift Schedule'
    _order = 'vehicle_id, station_sequence, shift_number, id'

    vehicle_id = fields.Many2one('transport.vehicle', string='المركبة', required=True, ondelete='cascade', index=True)
    route_id = fields.Many2one(related='vehicle_id.route_id', string='خط السير', store=True, readonly=True)
    station_id = fields.Many2one('transport.station', string='المحطة', required=True, ondelete='restrict', index=True)
    station_sequence = fields.Integer(related='station_id.sequence', string='ترتيب المحطة', store=True, readonly=True)
    shift_number = fields.Selection(
        [('1', 'الوردية الأولى'), ('2', 'الوردية الثانية'), ('3', 'الوردية الثالثة')],
        string='الوردية', required=True, default='1', index=True,
    )
    departure_time = fields.Float(string='وقت التحرك', required=True, default=0.0)
    notes = fields.Char(string='ملاحظات')

    _sql_constraints = [
        (
            'transport_vehicle_station_unique',
            'unique(vehicle_id, station_id, shift_number)',
            'تمت إضافة موعد لهذه المحطة في هذه الوردية لهذه المركبة بالفعل.',
        ),
    ]

    @api.constrains('vehicle_id', 'station_id')
    def _check_station_route(self):
        for schedule in self:
            if schedule.vehicle_id and schedule.station_id and schedule.vehicle_id.route_id != schedule.station_id.route_id:
                raise ValidationError(_('يجب أن تكون المحطة تابعة لخط سير المركبة.'))

    @api.constrains('departure_time')
    def _check_departure_time(self):
        for schedule in self:
            if not 0.0 <= schedule.departure_time < 24.0:
                raise ValidationError(_('وقت التحرك يجب أن يكون بين 00:00 و23:59.'))

    @api.constrains('vehicle_id', 'shift_number')
    def _check_shift_is_active(self):
        for schedule in self:
            if schedule.vehicle_id and int(schedule.shift_number) > int(schedule.vehicle_id.active_shifts):
                raise ValidationError(_(
                    'لا يمكن إضافة موعد للوردية %(shift)s لأن المركبة %(vehicle)s تعمل %(active)s فقط.'
                ) % {
                    'shift': schedule.shift_number,
                    'vehicle': schedule.vehicle_id.display_name,
                    'active': schedule.vehicle_id.active_shifts,
                })
