from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    _PORTAL_STATE_LABELS = {
        'draft': 'مسودة',
        'confirm': 'قيد الموافقة',
        'validate1': 'بانتظار الموافقة النهائية',
        'validate': 'معتمدة',
        'refuse': 'مرفوضة',
        'cancel': 'ملغاة',
    }

    @api.model
    def _portal_employee(self, employee_id):
        """Return an employee only when the caller may access its portal data."""
        employee = self.env['hr.employee'].sudo().browse(employee_id).exists()
        if not employee:
            raise UserError(_('تعذر العثور على سجل الموظف المرتبط بالحساب.'))
        if self.env.user.share and employee.user_id != self.env.user:
            raise AccessError(_('يمكنك الاطلاع على بيانات إجازاتك فقط.'))
        return employee

    @api.model
    def _portal_available_leave_types(self, employee, date_from=None, date_to=None):
        """Return employee-requestable types in the employee/date context."""
        date_from = fields.Date.to_date(date_from) if date_from else fields.Date.today()
        date_to = fields.Date.to_date(date_to) if date_to else date_from
        return self.env['hr.leave.type'].sudo().with_context(
            employee_id=employee.id,
            default_employee_id=employee.id,
            default_date_from=date_from,
            default_date_to=date_to,
        ).search([
            ('active', '=', True),
            ('portal_self_service', '=', True),
            ('manager_only_requests', '=', False),
            ('company_id', 'in', [employee.company_id.id, False]),
            '|',
                ('requires_allocation', '=', False),
                '&',
                    ('has_valid_allocation', '=', True),
                    '|',
                        ('allows_negative', '=', True),
                        ('virtual_remaining_leaves', '>', 0),
        ], order='sequence, id')

    @api.model
    def _portal_validate_leave_type(self, employee_id, leave_type_id, date_from, date_to):
        """Validate a submitted type instead of trusting the browser options."""
        employee = self._portal_employee(employee_id)
        leave_type = self._portal_available_leave_types(employee, date_from, date_to).filtered(
            lambda item: item.id == int(leave_type_id)
        )
        if not leave_type:
            raise UserError(_(
                'نوع الإجازة غير متاح، أو لا يوجد له رصيد صالح، أو لا يمكن طلبه إلا بواسطة مديرك.'
            ))
        return leave_type

    def _portal_employee_can_modify(self):
        """Whether the employee may safely change this request."""
        self.ensure_one()
        if self.holiday_status_id.manager_only_requests:
            return False
        if self.state == 'refuse':
            return True
        return self.state == 'confirm' and not any((
            self.supervisor_approved,
            self.manager_approved,
            self.clinical_approved,
        ))

    def _portal_approval_summary(self):
        """Return the real custom approval stage and its completed steps."""
        self.ensure_one()

        supervisor = self.department_supervisor_id
        manager = self.department_manager_id
        clinical_manager = self.clinical_manager_id if self.requires_clinical_approval else False

        if self.state == 'validate':
            stage_key, stage_label, stage_actor = 'approved', _('تم اعتماد الطلب بالكامل'), ''
        elif self.state == 'refuse':
            stage_key, stage_label, stage_actor = 'refused', _('تم رفض الطلب'), ''
        elif self.state == 'cancel':
            stage_key, stage_label, stage_actor = 'cancelled', _('تم إلغاء الطلب'), ''
        elif supervisor and not self.supervisor_approved:
            stage_key = 'supervisor'
            stage_label = _('بانتظار موافقة المشرف')
            stage_actor = supervisor.name
        elif manager and not self.manager_approved:
            stage_key = 'manager'
            stage_label = _('بانتظار موافقة المدير')
            stage_actor = manager.name
        elif clinical_manager and not self.clinical_approved:
            stage_key = 'clinical'
            stage_label = _('بانتظار الموافقة الطبية')
            stage_actor = clinical_manager.name
        else:
            stage_key = 'hr'
            stage_label = _('بانتظار الاعتماد النهائي من الموارد البشرية')
            stage_actor = ''

        def step_status(key, approved):
            if approved:
                return 'approved'
            if self.state in ('refuse', 'cancel'):
                return 'stopped'
            if stage_key == key:
                return 'pending'
            return 'waiting'

        steps = []
        if supervisor:
            steps.append({
                'key': 'supervisor',
                'label': _('المشرف'),
                'actor': supervisor.name,
                'status': step_status('supervisor', self.supervisor_approved),
            })
        if manager:
            steps.append({
                'key': 'manager',
                'label': _('المدير'),
                'actor': manager.name,
                'status': step_status('manager', self.manager_approved),
            })
        if clinical_manager:
            steps.append({
                'key': 'clinical',
                'label': _('الموافقة الطبية'),
                'actor': clinical_manager.name,
                'status': step_status('clinical', self.clinical_approved),
            })

        return {
            'approval_stage': stage_key,
            'approval_stage_label': stage_label,
            'approval_stage_actor': stage_actor,
            'approval_steps': steps,
        }

    def _portal_leave_payload(self):
        """Serialize one leave without exposing private employee data."""
        self.ensure_one()
        payload = {
            'id': self.id,
            'employee_id': self.employee_id.id,
            'employee_name': self.employee_id.name,
            'department_name': self.department_id.name or '',
            'leave_type': self.holiday_status_id.name,
            'leave_type_id': self.holiday_status_id.id,
            'leave_type_color': self.holiday_status_id.color,
            'is_assignment': self.holiday_status_id.manager_only_requests,
            'date_from': fields.Date.to_string(self.request_date_from) if self.request_date_from else '',
            'date_to': fields.Date.to_string(self.request_date_to) if self.request_date_to else '',
            'duration': self.number_of_days,
            'duration_display': self.duration_display,
            'description': self.private_name or '',
            'state': self.state,
            'state_label': _(self._PORTAL_STATE_LABELS.get(self.state, self.state)),
            'can_edit': self._portal_employee_can_modify(),
            'can_delete': self._portal_employee_can_modify(),
        }
        payload.update(self._portal_approval_summary())
        return payload

    @api.model
    def _portal_get_leaves(self, employee_id, status_filter='all', request_kind='timeoff'):
        """Return formatted leave data for the portal interface."""
        employee = self._portal_employee(employee_id)
        is_assignment = request_kind == 'assignment'
        domain = [
            ('employee_id', '=', employee.id),
            ('holiday_status_id.manager_only_requests', '=', is_assignment),
        ]
        if status_filter == 'pending':
            domain.append(('state', 'in', ['confirm', 'validate1']))
        elif status_filter == 'approved':
            domain.append(('state', '=', 'validate'))
        elif status_filter == 'refused':
            domain.append(('state', '=', 'refuse'))

        leaves = self.sudo().search(domain, order='date_from desc, id desc', limit=100)
        return [leave._portal_leave_payload() for leave in leaves]

    @api.model
    def _portal_managed_departments(self, manager_only=False):
        """Departments the current user manages or supervises."""
        domain = [('manager_id.user_id', '=', self.env.user.id)]
        if not manager_only:
            domain = ['|', *domain, ('supervisor_id.user_id', '=', self.env.user.id)]
        return self.env['hr.department'].sudo().search(domain)

    @api.model
    def _portal_can_manage_team(self):
        return bool(self._portal_managed_departments())

    def _portal_team_action_role(self):
        """Return the approval role available to the current user, if any."""
        self.ensure_one()
        user = self.env.user
        if self.employee_id.user_id == user or self.state != 'confirm':
            return False
        is_supervisor = self.department_supervisor_id.user_id == user
        is_manager = self.department_manager_id.user_id == user
        if is_supervisor and not self.supervisor_approved:
            return 'supervisor'
        supervisor_done = not self.department_supervisor_id or self.supervisor_approved
        if is_manager and supervisor_done and not self.manager_approved:
            return 'manager'
        return False

    @api.model
    def _portal_get_team_leaves(self, status_filter='all'):
        departments = self._portal_managed_departments()
        if not departments:
            return []
        domain = [
            ('department_id', 'in', departments.ids),
            ('employee_id.user_id', '!=', self.env.user.id),
        ]
        if status_filter == 'pending':
            domain.append(('state', 'in', ['confirm', 'validate1']))
        elif status_filter == 'approved':
            domain.append(('state', '=', 'validate'))
        elif status_filter == 'refused':
            domain.append(('state', '=', 'refuse'))

        result = []
        for leave in self.sudo().search(domain, order='date_from desc, id desc', limit=200):
            payload = leave._portal_leave_payload()
            action_role = leave._portal_team_action_role()
            payload.update({
                'can_approve': bool(action_role),
                'can_refuse': bool(action_role),
                'action_role': action_role or '',
                'action_role_label': _(
                    'موافقة المشرف' if action_role == 'supervisor' else 'موافقة المدير'
                ) if action_role else '',
                'can_edit': False,
                'can_delete': False,
            })
            result.append(payload)
        return result

    @api.model
    def _portal_get_assignment_employees(self):
        departments = self._portal_managed_departments(manager_only=True)
        if not departments:
            return []
        employees = self.env['hr.employee'].sudo().search([
            ('active', '=', True),
            ('department_id', 'in', departments.ids),
            ('user_id', '!=', self.env.user.id),
        ], order='name, id')
        return [{
            'id': employee.id,
            'name': employee.name,
            'department': employee.department_id.name or '',
        } for employee in employees]

    @api.model
    def _portal_get_assignment_types(self):
        departments = self._portal_managed_departments(manager_only=True)
        company_ids = departments.mapped('company_id').ids
        if not departments:
            return []
        leave_types = self.env['hr.leave.type'].sudo().search([
            ('active', '=', True),
            ('manager_only_requests', '=', True),
            ('company_id', 'in', [False, *company_ids]),
        ], order='sequence, id')
        return [{'id': leave_type.id, 'name': leave_type.name} for leave_type in leave_types]

    def _portal_apply_team_action(self, action):
        """Approve/refuse only the caller's currently assigned department stage."""
        self.ensure_one()
        role = self._portal_team_action_role()
        if not role:
            raise AccessError(_('لا تملك صلاحية تنفيذ هذا الإجراء، أو أن الطلب ليس في مرحلتك الحالية.'))
        if action == 'approve':
            method_name = f'action_{role}_approve'
        elif action == 'refuse':
            method_name = f'action_{role}_refuse'
        else:
            raise UserError(_('الإجراء المطلوب غير صالح.'))
        getattr(self.sudo(), method_name)()
        return role

    @api.model
    def _portal_get_balances(self, employee_id):
        """Return leave type balances for the portal dashboard."""
        employee = self._portal_employee(employee_id)

        leave_types = self.env['hr.leave.type'].sudo().search([
            ('requires_allocation', '=', True),
            ('manager_only_requests', '=', False),
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
        employee = self._portal_employee(employee_id)
        leave_types = self._portal_available_leave_types(employee)

        return [{
            'id': lt.id,
            'name': lt.name,
            'color': lt.color,
            'request_unit': lt.request_unit,
            'requires_allocation': lt.requires_allocation,
        } for lt in leave_types]
