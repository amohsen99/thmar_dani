from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.addons.portal.controllers.portal import CustomerPortal

class PortalTimeOff(CustomerPortal):

    _PORTAL_POLICY_CONTEXT = {'skip_thamar_leave_policy_checks': True}

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        values['can_manage_team'] = request.env['hr.leave']._portal_can_manage_team()
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        requested_counters = {'timeoff_count'}.intersection(counters)
        if requested_counters:
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
            raise AccessError(_("لا يوجد سجل موظف مرتبط بحسابك."))
        return employee

    def _parse_positive_id(self, value, label):
        try:
            record_id = int(value)
        except (TypeError, ValueError):
            raise UserError(_('%s غير صالح.', label))
        if record_id <= 0:
            raise UserError(_('%s غير صالح.', label))
        return record_id

    def _parse_date_range(self, date_from, date_to):
        try:
            parsed_date_from = fields.Date.to_date(date_from)
            parsed_date_to = fields.Date.to_date(date_to)
        except (TypeError, ValueError):
            raise UserError(_('أدخل تاريخ بداية وتاريخ نهاية صالحين.'))
        if not parsed_date_from or not parsed_date_to:
            raise UserError(_('تاريخ البداية وتاريخ النهاية مطلوبان.'))
        if parsed_date_from > parsed_date_to:
            raise UserError(_('يجب أن يكون تاريخ النهاية مساوياً لتاريخ البداية أو بعده.'))
        return parsed_date_from, parsed_date_to

    def _prepare_leave_values(self, employee, leave_type_id, date_from, date_to, description):
        parsed_date_from, parsed_date_to = self._parse_date_range(date_from, date_to)

        leave_type_id = self._parse_positive_id(leave_type_id, _('نوع الإجازة'))
        request.env['hr.leave']._portal_validate_leave_type(
            employee.id, leave_type_id, parsed_date_from, parsed_date_to,
        )
        description = (description or '').strip()
        if len(description) > 500:
            raise UserError(_('لا يمكن أن يتجاوز الوصف 500 حرف.'))
        return {
            'employee_id': employee.id,
            'holiday_status_id': leave_type_id,
            'request_date_from': parsed_date_from,
            'request_date_to': parsed_date_to,
            'private_name': description or False,
        }

    def _prepare_team_leave_values(self, employee_id, leave_type_id, date_from, date_to, description):
        HrLeave = request.env['hr.leave']
        managed_departments = HrLeave._portal_managed_departments()
        employee_id = self._parse_positive_id(employee_id, _('الموظف'))
        employee = request.env['hr.employee'].sudo().browse(employee_id).exists()
        if not employee or employee.department_id not in managed_departments:
            raise AccessError(_('يمكنك إنشاء إجازة لموظفي الأقسام التي تديرها أو تشرف عليها فقط.'))
        if employee.user_id == request.env.user:
            raise AccessError(_('استخدم شاشة «إجازاتي» لإنشاء إجازة لنفسك.'))

        parsed_date_from, parsed_date_to = self._parse_date_range(date_from, date_to)
        leave_type_id = self._parse_positive_id(leave_type_id, _('نوع الإجازة'))
        leave_type = HrLeave._portal_available_leave_types(
            employee, parsed_date_from, parsed_date_to,
        ).filtered(lambda item: item.id == leave_type_id)
        if not leave_type:
            raise UserError(_('نوع الإجازة المحدد غير متاح لهذا الموظف أو لا يوجد له رصيد صالح.'))

        description = (description or '').strip()
        if len(description) > 500:
            raise UserError(_('لا يمكن أن يتجاوز الوصف 500 حرف.'))
        return {
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': parsed_date_from,
            'request_date_to': parsed_date_to,
            'private_name': description or False,
        }

    def _portal_error(self, error):
        return {'success': False, 'message': str(error)}

    # ── Portal Page ─────────────────────────────────────────────────
    @http.route('/my/timeoff', type='http', auth='user', website=True)
    def portal_timeoff(self, scope='mine', **kw):
        values = self._prepare_portal_layout_values()
        values['page_name'] = 'timeoff'
        values['timeoff_team'] = scope == 'team' and values['can_manage_team']
        try:
            employee = self._get_employee()
            values['employee_id'] = employee.id
            values['employee_name'] = employee.name
        except AccessError:
            values['employee_id'] = False
            values['employee_name'] = ''
        return request.render('thamar_portal_timeoff.portal_timeoff_page', values)

    @http.route('/my/assignments', type='http', auth='user', website=True)
    def portal_assignments(self, **kw):
        """Keep old bookmarks working after merging assignments into Time Off."""
        return request.redirect('/my/timeoff')

    @http.route('/my/team/timeoff', type='http', auth='user', website=True)
    def portal_team_timeoff(self, **kw):
        """Keep old bookmarks working after merging team leave management."""
        if not request.env['hr.leave']._portal_can_manage_team():
            return request.not_found()
        return request.redirect('/my/timeoff?scope=team')

    # ── JSON-RPC Endpoints ──────────────────────────────────────────
    @http.route('/my/timeoff/data', type='jsonrpc', auth='user', website=True, readonly=True, methods=['POST'])
    def portal_timeoff_data(self, status_filter='all', **kw):
        employee = self._get_employee()
        HrLeave = request.env['hr.leave']
        return {
            'leaves': HrLeave._portal_get_leaves(employee.id, status_filter),
            'balances': HrLeave._portal_get_balances(employee.id),
            'leave_types': HrLeave._portal_get_leave_types(employee.id),
            'employee_name': employee.name,
        }

    @http.route('/my/team/timeoff/data', type='jsonrpc', auth='user', website=True, readonly=True, methods=['POST'])
    def portal_team_timeoff_data(self, status_filter='all', **kw):
        HrLeave = request.env['hr.leave']
        if not HrLeave._portal_can_manage_team():
            raise AccessError(_('لا تملك صلاحية إدارة إجازات فريق.'))
        employees = HrLeave._portal_get_team_leave_employees()
        leave_types = HrLeave._portal_get_team_leave_types(employees)
        return {
            'leaves': HrLeave._portal_get_team_leaves(status_filter),
            'employees': employees,
            'leave_types': leave_types,
            'can_create_leaves': bool(employees and leave_types),
        }

    @http.route('/my/team/timeoff/action', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def portal_team_timeoff_action(self, leave_id, action, **kw):
        try:
            leave_id = self._parse_positive_id(leave_id, _('طلب الإجازة'))
            leave = request.env['hr.leave'].sudo().browse(leave_id).exists()
            if not leave:
                raise UserError(_('تعذر العثور على طلب الإجازة.'))
            role = leave._portal_apply_team_action(action)
            role_label = _('المشرف') if role == 'supervisor' else _('المدير')
            action_label = _('اعتماد') if action == 'approve' else _('رفض')
            return {
                'success': True,
                'message': _('%(action)s الطلب بواسطة %(role)s بنجاح.', action=action_label, role=role_label),
            }
        except (AccessError, UserError, ValidationError) as error:
            return self._portal_error(error)

    @http.route('/my/team/timeoff/create', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def portal_team_leave_create(
        self, employee_id, leave_type_id, date_from, date_to, description='', **kw
    ):
        try:
            values = self._prepare_team_leave_values(
                employee_id, leave_type_id, date_from, date_to, description,
            )
            leave = request.env['hr.leave'].with_context(
                **self._PORTAL_POLICY_CONTEXT
            ).sudo().create(values)
            return {
                'success': True,
                'leave_id': leave.id,
                'message': _('تم إنشاء طلب الإجازة للموظف بنجاح.'),
            }
        except (AccessError, UserError, ValidationError) as error:
            return self._portal_error(error)

    @http.route('/my/timeoff/create', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def portal_timeoff_create(self, leave_type_id, date_from, date_to, description='', **kw):
        employee = self._get_employee()
        try:
            values = self._prepare_leave_values(
                employee, leave_type_id, date_from, date_to, description,
            )
            leave = request.env['hr.leave'].with_context(
                **self._PORTAL_POLICY_CONTEXT
            ).sudo().create(values)
            return {
                'success': True,
                'leave_id': leave.id,
                'message': _("تم إنشاء طلب الإجازة بنجاح."),
            }
        except (AccessError, UserError, ValidationError) as error:
            return self._portal_error(error)

    @http.route('/my/timeoff/update', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def portal_timeoff_update(self, leave_id, leave_type_id, date_from, date_to, description='', **kw):
        employee = self._get_employee()
        try:
            leave_id = self._parse_positive_id(leave_id, _('طلب الإجازة'))
            leave = request.env['hr.leave'].sudo().browse(leave_id).exists()
            if not leave or leave.employee_id.id != employee.id:
                raise UserError(_('تعذر العثور على طلب الإجازة.'))
            if not leave._portal_employee_can_modify():
                raise UserError(_(
                    'لا يمكن تعديل الطلب بعد تسجيل إحدى الموافقات عليه.'
                ))

            values = self._prepare_leave_values(
                employee, leave_type_id, date_from, date_to, description,
            )
            if leave.state == 'refuse':
                values.update({
                    'state': 'confirm',
                    'supervisor_approved': False,
                    'manager_approved': False,
                    'clinical_approved': False,
                })
            leave.with_context(**self._PORTAL_POLICY_CONTEXT).write(values)
            return {
                'success': True,
                'message': _("تم تحديث طلب الإجازة بنجاح."),
            }
        except (AccessError, UserError, ValidationError) as error:
            return self._portal_error(error)

    @http.route('/my/timeoff/delete', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def portal_timeoff_delete(self, leave_id, **kw):
        employee = self._get_employee()
        try:
            leave_id = self._parse_positive_id(leave_id, _('طلب الإجازة'))
            leave = request.env['hr.leave'].sudo().browse(leave_id).exists()
            if not leave or leave.employee_id.id != employee.id:
                raise UserError(_('تعذر العثور على طلب الإجازة.'))
            if not leave._portal_employee_can_modify():
                raise UserError(_(
                    'لا يمكن حذف الطلب بعد تسجيل إحدى الموافقات عليه.'
                ))
            leave.unlink()
            return {
                'success': True,
                'message': _("تم حذف طلب الإجازة بنجاح."),
            }
        except (AccessError, UserError, ValidationError) as error:
            return self._portal_error(error)

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
    @http.route('/my/employee/data', type='jsonrpc', auth='user', website=True, readonly=True, methods=['POST'])
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
            'address': emp.address_id.display_name if emp.address_id else '',
            'work_location': emp.work_location_id.name if emp.work_location_id else '',
            'tz': tz,
            'employee_type': selection_label('employee_type', emp.employee_type),
            'resource_calendar': calendar.name if calendar else '',
            'schedule_lines': schedule_lines,
            'identification_id': emp.identification_id or '',
            'passport_id': emp.passport_id or '',
            # Odoo 19 renamed the employee field from ``gender`` to ``sex``.
            'gender': selection_label('sex', emp.sex),
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
            'supervisor_id': fmt_many2one(emp.department_id.supervisor_id) if emp.department_id else '',
        }
        return data
