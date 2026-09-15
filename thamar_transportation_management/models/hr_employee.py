# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    transport_route_id = fields.Many2one('transport.route', string='خط السير', index=True)
    transport_vehicle_id = fields.Many2one(
        'transport.vehicle', string='المركبة', index=True,
        domain="[('route_id', '=', transport_route_id), ('remaining_seats', '>', 0)]",
    )
    transport_fixed_first_shift = fields.Boolean(string='ثابت بالوردية الأولى', default=False)

    @api.onchange('transport_route_id')
    def _onchange_transport_route_id(self):
        # Keep the prefilled vehicle when opening an employee from that vehicle.
        # Clear it only when the user selects a route that does not own it.
        if self.transport_vehicle_id and self.transport_vehicle_id.route_id != self.transport_route_id:
            self.transport_vehicle_id = False

    @api.constrains('transport_route_id', 'transport_vehicle_id', 'transport_fixed_first_shift')
    def _check_transport_assignment(self):
        for employee in self:
            vehicle = employee.transport_vehicle_id
            if not vehicle:
                continue
            if employee.transport_route_id != vehicle.route_id:
                raise ValidationError(_(
                    'يجب أن تكون المركبة المختارة تابعة لخط سير الموظف.'
                ))
            if vehicle.occupied_seats > vehicle.effective_capacity:
                message = _(
                    'المركبة %(vehicle)s مكتملة العدد ولا يمكن تسكين موظفين إضافيين بها.'
                ) % {'vehicle': vehicle.display_name}
                raise ValidationError(message)
            if employee.transport_fixed_first_shift and vehicle.fixed_first_shift_passengers > vehicle.standard_capacity:
                raise ValidationError(_(
                    'لا يمكن تسكين الموظف بالوردية الأولى؛ لا توجد مقاعد شاغرة في الوردية الأولى للمركبة %(vehicle)s.'
                ) % {'vehicle': vehicle.display_name})


class HrEmployeePublic(models.Model):
    """Expose transportation fields to department-level HR views.

    Odoo uses ``hr.employee.public`` in views available to users who do not
    have access to private employee records, including department time-off.
    """

    _inherit = 'hr.employee.public'

    transport_route_id = fields.Many2one(
        related='employee_id.transport_route_id', string='خط السير', readonly=True,
    )
    transport_vehicle_id = fields.Many2one(
        related='employee_id.transport_vehicle_id', string='المركبة', readonly=True,
    )
    transport_fixed_first_shift = fields.Boolean(
        related='employee_id.transport_fixed_first_shift', string='ثابت بالوردية الأولى', readonly=True,
    )
