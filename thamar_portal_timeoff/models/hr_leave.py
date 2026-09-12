from odoo import api, fields, models, _


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def _portal_get_leaves(self, employee_id, status_filter='all'):
        """Return formatted leave data for the portal interface."""
        domain = [('employee_id', '=', employee_id)]
        if status_filter == 'pending':
            domain.append(('state', 'in', ['confirm', 'validate1']))
        elif status_filter == 'approved':
            domain.append(('state', '=', 'validate'))
        elif status_filter == 'refused':
            domain.append(('state', '=', 'refuse'))

        leaves = self.sudo().search(domain, order='date_from desc', limit=100)
        result = []
        for leave in leaves:
            result.append({
                'id': leave.id,
                'leave_type': leave.holiday_status_id.name,
                'leave_type_id': leave.holiday_status_id.id,
                'leave_type_color': leave.holiday_status_id.color,
                'date_from': fields.Date.to_string(leave.request_date_from) if leave.request_date_from else '',
                'date_to': fields.Date.to_string(leave.request_date_to) if leave.request_date_to else '',
                'duration': leave.number_of_days,
                'duration_display': leave.duration_display,
                'description': leave.name or '',
                'state': leave.state,
                'state_label': dict(leave._fields['state'].selection).get(leave.state, ''),
                'can_edit': leave.state in ('confirm', 'refuse'),
                'can_delete': leave.state in ('confirm', 'refuse'),
            })
        return result

    @api.model
    def _portal_get_balances(self, employee_id):
        """Return leave type balances for the portal dashboard."""
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        if not employee.exists():
            return []

        leave_types = self.env['hr.leave.type'].sudo().search([
            ('requires_allocation', '=', True),
            '|',
            ('company_id', '=', employee.company_id.id),
            ('company_id', '=', False),
        ])

        result = []
        today = fields.Date.today()
        allocation_data = employee._get_consumed_leaves(leave_types, today)[0]

        for lt in leave_types:
            max_leaves = 0
            remaining = 0
            for _alloc, alloc_data in allocation_data.get(employee, {}).get(lt, {}).items():
                max_leaves += alloc_data.get('max_leaves', 0)
                remaining += alloc_data.get('virtual_remaining_leaves', 0)

            if max_leaves > 0:
                result.append({
                    'id': lt.id,
                    'name': lt.name,
                    'color': lt.color,
                    'max_leaves': max_leaves,
                    'remaining': remaining,
                    'taken': max_leaves - remaining,
                    'percentage': round((max_leaves - remaining) / max_leaves * 100) if max_leaves else 0,
                })

        return result

    @api.model
    def _portal_get_leave_types(self, employee_id):
        """Return leave types the selected employee can actually use.

        ``has_valid_allocation`` and ``virtual_remaining_leaves`` are computed
        in the context of an employee.  Without that context Odoo evaluates
        the allocation against the system user, hiding annual and casual leave
        types even when the portal employee has a positive allocation.
        """
        employee = self.env['hr.employee'].sudo().browse(employee_id).exists()
        if not employee:
            return []

        today = fields.Date.today()
        leave_types = self.env['hr.leave.type'].sudo().with_context(
            employee_id=employee.id,
            default_employee_id=employee.id,
            default_date_from=today,
            default_date_to=today,
        ).search([
            '|',
                ('requires_allocation', '=', False),
                '&',
                    ('has_valid_allocation', '=', True),
                    '|',
                        ('allows_negative', '=', True),
                        '&',
                            ('virtual_remaining_leaves', '>', 0),
                            ('allows_negative', '=', False),
            ('company_id', 'in', [employee.company_id.id, False]),
        ], order='sequence')

        return [{
            'id': lt.id,
            'name': lt.name,
            'color': lt.color,
            'request_unit': lt.request_unit,
            'requires_allocation': lt.requires_allocation,
        } for lt in leave_types]
