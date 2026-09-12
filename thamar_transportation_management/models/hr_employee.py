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

    @api.onchange('transport_route_id')
    def _onchange_transport_route_id(self):
        # Keep the prefilled vehicle when opening an employee from that vehicle.
        # Clear it only when the user selects a route that does not own it.
        if self.transport_vehicle_id and self.transport_vehicle_id.route_id != self.transport_route_id:
            self.transport_vehicle_id = False

    @api.constrains('transport_route_id', 'transport_vehicle_id')
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
