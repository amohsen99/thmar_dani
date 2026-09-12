import logging
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class PortalTimeOff(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'timeoff_count' in counters:
            employee = request.env.user.employee_id
            if employee:
                values['timeoff_count'] = request.env['hr.leave'].sudo().search_count([
                    ('employee_id', '=', employee.id),
                ])
            else:
                values['timeoff_count'] = 0
        return values

    def _get_employee(self):
        """Get the employee linked to the current portal user."""
        employee = request.env.user.sudo().employee_id
        if not employee:
            raise AccessError(_("No employee record is linked to your account."))
        return employee

    # ── Portal Page ─────────────────────────────────────────────────
    @http.route('/my/timeoff', type='http', auth='user', website=True)
    def portal_timeoff(self, **kw):
        values = self._prepare_portal_layout_values()
        values['page_name'] = 'timeoff'
        try:
            employee = self._get_employee()
            values['employee_id'] = employee.id
            values['employee_name'] = employee.name
        except AccessError:
            values['employee_id'] = False
            values['employee_name'] = ''
        return request.render('thamar_portal_timeoff.portal_timeoff_page', values)

    # ── JSON-RPC Endpoints ──────────────────────────────────────────
    @http.route('/my/timeoff/data', type='json', auth='user', website=True, readonly=True)
    def portal_timeoff_data(self, status_filter='all', **kw):
        employee = self._get_employee()
        HrLeave = request.env['hr.leave']
        return {
            'leaves': HrLeave._portal_get_leaves(employee.id, status_filter),
            'balances': HrLeave._portal_get_balances(employee.id),
            'leave_types': HrLeave._portal_get_leave_types(employee.id),
            'employee_name': employee.name,
        }

    @http.route('/my/timeoff/create', type='json', auth='user', website=True)
    def portal_timeoff_create(self, leave_type_id, date_from, date_to, description='', **kw):
        employee = self._get_employee()
        try:
            leave = request.env['hr.leave'].sudo().create({
                'employee_id': employee.id,
                'holiday_status_id': int(leave_type_id),
                'request_date_from': date_from,
                'request_date_to': date_to,
                'private_name': description or False,
            })
            return {
                'success': True,
                'leave_id': leave.id,
                'message': _("Time off request created successfully."),
            }
        except (UserError, ValidationError) as e:
            return {
                'success': False,
                'message': str(e),
            }

    @http.route('/my/timeoff/update', type='json', auth='user', website=True)
    def portal_timeoff_update(self, leave_id, leave_type_id, date_from, date_to, description='', **kw):
        employee = self._get_employee()
        leave = request.env['hr.leave'].sudo().browse(int(leave_id))

        if not leave.exists() or leave.employee_id.id != employee.id:
            return {'success': False, 'message': _("Leave not found.")}

        if leave.state not in ('confirm', 'refuse'):
            return {'success': False, 'message': _("Only draft or refused requests can be edited.")}

        try:
            # If refused, reset to draft first
            if leave.state == 'refuse':
                leave.action_draft()

            leave.write({
                'holiday_status_id': int(leave_type_id),
                'request_date_from': date_from,
                'request_date_to': date_to,
                'private_name': description or False,
            })
            return {
                'success': True,
                'message': _("Time off request updated successfully."),
            }
        except (UserError, ValidationError) as e:
            return {
                'success': False,
                'message': str(e),
            }

    @http.route('/my/timeoff/delete', type='json', auth='user', website=True)
    def portal_timeoff_delete(self, leave_id, **kw):
        employee = self._get_employee()
        leave = request.env['hr.leave'].sudo().browse(int(leave_id))

        if not leave.exists() or leave.employee_id.id != employee.id:
            return {'success': False, 'message': _("Leave not found.")}

        if leave.state not in ('confirm', 'refuse'):
            return {'success': False, 'message': _("Only draft or refused requests can be deleted.")}

        try:
            # If refused, reset to draft first so it can be unlinked
            if leave.state == 'refuse':
                leave.action_draft()
            leave.unlink()
            return {
                'success': True,
                'message': _("Time off request deleted successfully."),
            }
        except (UserError, ValidationError) as e:
            return {
                'success': False,
                'message': str(e),
            }

    # ── Employee Info Portal Page ───────────────────────────────────
    @http.route('/my/employee', type='http', auth='user', website=True)
    def portal_employee(self, **kw):
        values = self._prepare_portal_layout_values()
        values['page_name'] = 'employee'
        try:
            employee = self._get_employee()
            values['employee_id'] = employee.id
            values['employee_name'] = employee.name
        except AccessError:
            values['employee_id'] = False
            values['employee_name'] = ''
        return request.render('thamar_portal_timeoff.portal_employee_page', values)

    # ── Employee Info JSON-RPC ──────────────────────────────────────
    @http.route('/my/employee/data', type='json', auth='user', website=True, readonly=True)
    def portal_employee_data(self, **kw):
        employee = self._get_employee()
        emp = employee.sudo()
        lang = request.env.context.get('lang') or 'en_US'
        formatted = self._format_employee(emp, lang)
        return {
            'employee': formatted,
            'employee_name': emp.name,
        }

    def _format_employee(self, emp, lang):
        """Return a serializable dict of employee fields for the portal."""
        tz = emp.tz or 'UTC'
        calendar = emp.resource_calendar_id
        schedule_lines = []
        if calendar:
            for line in calendar.sudo().attendance_ids:
                schedule_lines.append({
                    'day': line.dayofweek,
                    'day_name': dict(line._fields['dayofweek'].selection).get(line.dayofweek, ''),
                    'hour_from': line.hour_from,
                    'hour_to': line.hour_to,
                })

        def fmt_dt(dt):
            if not dt:
                return ''
            return fields.Datetime.to_string(dt)

        def fmt_date(d):
            if not d:
                return ''
            return fields.Date.to_string(d)

        def fmt_many2one(field):
            return field.name if field else ''

        def selection_label(field_name, val):
            if not val:
                return ''
            field = emp._fields.get(field_name)
            if not field:
                return str(val)
            selection = field.selection
            if callable(selection):
                selection = selection(emp)
            if not selection:
                return str(val)
            return dict(selection).get(val, str(val))

        # Build the employee data structure
        data = {
            'id': emp.id,
            'name': emp.name,
            'work_email': emp.work_email or '',
            'work_phone': emp.work_phone or '',
            'mobile_phone': emp.mobile_phone or '',
            'job_id': fmt_many2one(emp.job_id),
            'department_id': fmt_many2one(emp.department_id),
            'manager_id': fmt_many2one(emp.parent_id),
            'coach_id': fmt_many2one(emp.coach_id),
            'address': emp.address_id.name_get()[0][1] if emp.address_id else '',
            'work_location': emp.work_location or '',
            'tz': tz,
            'employee_type': selection_label('employee_type', emp.employee_type),
            'resource_calendar': calendar.name if calendar else '',
            'schedule_lines': schedule_lines,
            'identification_id': emp.identification_id or '',
            'passport_id': emp.passport_id or '',
            'gender': selection_label('gender', emp.gender),
            'marital': selection_label('marital', emp.marital),
            'birthday': fmt_date(emp.birthday),
            'country_id': emp.country_id.name if emp.country_id else '',
            'country_of_birth': emp.country_of_birth.name if emp.country_of_birth else '',
            'place_of_birth': emp.place_of_birth or '',
            'km_home_work': emp.km_home_work or 0,
            'emergency_contact': emp.emergency_contact or '',
            'emergency_phone': emp.emergency_phone or '',
            'hire_date': fmt_dt(emp.hire_date),
            'admin_type': selection_label('admin_type', emp.admin_type),
            'supervisor_id': fmt_many2one(emp.supervisor_id),
        }
        return data
