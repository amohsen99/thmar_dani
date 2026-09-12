# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class TransportVehicleAssignEmployeeWizard(models.TransientModel):
    _name = 'transport.vehicle.assign.employee.wizard'
    _description = 'Assign Employees to Transportation Vehicle'

    vehicle_id = fields.Many2one('transport.vehicle', string='المركبة', required=True, readonly=True)
    route_id = fields.Many2one(related='vehicle_id.route_id', string='خط السير', readonly=True)
    employee_ids = fields.Many2many('hr.employee', string='الموظفون', required=True)

    def action_assign_employees(self):
        self.ensure_one()
        vehicle = self.vehicle_id
        employees_to_add = self.employee_ids - vehicle.passenger_ids
        if len(employees_to_add) > vehicle.remaining_seats:
            raise ValidationError(_(
                'لا يمكن تسكين %(count)s موظف. المتاح في المركبة %(available)s مقعد فقط.'
            ) % {
                'count': len(employees_to_add),
                'available': vehicle.remaining_seats,
            })

        self.employee_ids.write({
            'transport_route_id': vehicle.route_id.id,
            'transport_vehicle_id': vehicle.id,
        })
        return {'type': 'ir.actions.act_window_close'}
