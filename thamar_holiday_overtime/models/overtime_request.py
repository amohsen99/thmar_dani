from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class OvertimeRequest(models.Model):
    _name = 'thamar.overtime.request'
    _description = 'Overtime Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'
    _check_company_auto = True

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    employee_id = fields.Many2one('hr.employee', required=True, check_company=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    kind = fields.Selection([
        ('holiday_day', 'تشغيل يوم عطلة / عيد (أجر يومين)'),
        ('hours', 'ساعات إضافية نهارية / مسائية'),
        ('holiday_hours', 'ساعات إضافية في الراحة الأسبوعية / العطلات'),
        ('mission', 'مأمورية خارج محل العمل'),
    ], required=True, default='hours', tracking=True)
    date_start = fields.Datetime(required=True, tracking=True)
    date_stop = fields.Datetime(required=True, tracking=True)
    reason = fields.Text(required=True, tracking=True)
    timezone = fields.Char(readonly=True, required=True, default='UTC')
    state = fields.Selection([
        ('draft', 'مسودة'), ('supervisor', 'بانتظار المشرف'),
        ('manager', 'بانتظار رئيس القسم'), ('hr', 'بانتظار اعتماد الموارد البشرية'),
        ('approved', 'معتمد'),
        ('refused', 'مرفوض'), ('cancelled', 'ملغى'),
    ], default='draft', readonly=True, copy=False, tracking=True)
    supervisor_user_id = fields.Many2one('res.users', readonly=True, copy=False)
    manager_user_id = fields.Many2one('res.users', readonly=True, copy=False)
    hr_user_id = fields.Many2one('res.users', readonly=True, copy=False)
    supervisor_approved_at = fields.Datetime(readonly=True, copy=False)
    manager_approved_at = fields.Datetime(readonly=True, copy=False)
    hr_approved_at = fields.Datetime(readonly=True, copy=False)
    work_entry_ids = fields.One2many('hr.work.entry', 'overtime_request_id', readonly=True)
    duration = fields.Float(compute='_compute_duration', string='الساعات')
    can_manage = fields.Boolean(compute='_compute_permissions')
    can_approve = fields.Boolean(compute='_compute_permissions')
    can_hr_approve = fields.Boolean(compute='_compute_permissions')

    @api.depends('date_start', 'date_stop')
    def _compute_duration(self):
        for rec in self:
            rec.duration = (rec.date_stop - rec.date_start).total_seconds() / 3600 if rec.date_start and rec.date_stop else 0

    @api.depends_context('uid')
    @api.depends('employee_id', 'department_id', 'state')
    def _compute_permissions(self):
        for rec in self:
            rec.can_manage = rec._is_department_approver()
            rec.can_approve = bool(rec._approval_role())
            rec.can_hr_approve = rec._is_hr_approver() and rec.state == 'hr'

    @api.model
    def _managed_departments(self):
        return self.env['hr.department'].sudo().search([
            ('company_id', 'in', self.env.companies.ids),
            '|', ('supervisor_id.user_id', '=', self.env.uid), ('manager_id.user_id', '=', self.env.uid),
        ])

    def _is_department_approver(self):
        self.ensure_one()
        rec = self.sudo()
        return bool(rec.employee_id and rec.company_id in self.env.companies
                    and rec.employee_id.user_id.id != self.env.uid
                    and self.env.uid in (rec.department_id.supervisor_id.user_id.id,
                                         rec.department_id.manager_id.user_id.id))

    def _approval_role(self):
        self.ensure_one()
        rec = self.sudo()
        if not self._is_department_approver():
            return False
        if rec.state == 'supervisor' and rec.department_id.supervisor_id.user_id.id == self.env.uid:
            return 'supervisor'
        if rec.state == 'manager' and rec.department_id.manager_id.user_id.id == self.env.uid:
            return 'manager'
        return False

    def _is_hr_approver(self):
        self.ensure_one()
        return bool(self.env.user.has_group('thamar_holiday_overtime.group_overtime_hr_admin'))

    def _check_manager(self):
        if any(not rec._is_department_approver() for rec in self):
            raise AccessError(_('يسمح فقط لمشرف أو رئيس قسم الموظف بإدارة طلبه، ولا يمكن إدارة طلب يخصك.'))

    @api.model_create_multi
    def create(self, vals_list):
        allowed = {'employee_id', 'company_id', 'kind', 'date_start', 'date_stop', 'reason'}
        for vals in vals_list:
            if set(vals) - allowed:
                raise AccessError(_('لا يمكن تعيين حقول الموافقة أو الحقول الداخلية مباشرة.'))
            employee = self.env['hr.employee'].sudo().browse(vals.get('employee_id')).exists()
            if not employee or employee.department_id not in self._managed_departments() or employee.user_id.id == self.env.uid:
                raise AccessError(_('يمكن إنشاء طلب لموظفي أقسامك فقط، ولا يمكن إنشاء طلب لنفسك.'))
            vals['company_id'] = employee.company_id.id
            vals['timezone'] = employee.resource_calendar_id.tz or employee.company_id.resource_calendar_id.tz or 'UTC'
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('thamar.overtime.request') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        self._lock()
        self._check_manager()
        if set(vals) - {'employee_id', 'kind', 'date_start', 'date_stop', 'reason'}:
            raise AccessError(_('استخدم أزرار سير العمل لتغيير حالة الطلب.'))
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_('يمكن تعديل المسودات فقط. ألغ الطلب وأنشئ طلباً جديداً لتصحيحه.'))
        if 'employee_id' in vals:
            employee = self.env['hr.employee'].sudo().browse(vals['employee_id']).exists()
            if not employee or employee.department_id not in self._managed_departments():
                raise AccessError(_('الموظف خارج أقسامك.'))
            vals = dict(vals, company_id=employee.company_id.id,
                        timezone=employee.resource_calendar_id.tz or employee.company_id.resource_calendar_id.tz or 'UTC')
        result = super().write(vals)
        self._check_manager()
        return result

    def unlink(self):
        self._lock()
        self._check_manager()
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_('لا يمكن حذف طلب تم إرساله؛ استخدم الإلغاء.'))
        return super().unlink()

    @api.constrains('date_start', 'date_stop', 'employee_id', 'kind', 'reason')
    def _check_dates(self):
        for rec in self:
            if rec.date_stop <= rec.date_start:
                raise ValidationError(_('وقت النهاية يجب أن يأتي بعد وقت البداية.'))
            if rec.date_stop - rec.date_start > timedelta(days=31):
                raise ValidationError(_('الحد الأقصى للطلب 31 يوماً.'))
            if not (rec.reason or '').strip():
                raise ValidationError(_('سبب العمل الإضافي مطلوب.'))
            if rec.kind == 'holiday_day' and len(rec._daily_segments()) != 1:
                raise ValidationError(_('طلب تشغيل يوم عطلة يخص يوماً محلياً واحداً فقط.'))

    def _daily_segments(self):
        self.ensure_one()
        tz = pytz.timezone(self.timezone)
        start = pytz.utc.localize(self.date_start).astimezone(tz)
        stop = pytz.utc.localize(self.date_stop).astimezone(tz)
        result = []
        day = start.date()
        while day <= stop.date():
            left = max(start, tz.localize(datetime.combine(day, time.min)))
            right = min(stop, tz.localize(datetime.combine(day + timedelta(days=1), time.min)))
            if right > left:
                result.append((day, left, right))
            day += timedelta(days=1)
        return result

    def _lock(self):
        if not self:
            return
        self.flush_recordset()
        self.env.cr.execute('SELECT id FROM thamar_overtime_request WHERE id IN %s ORDER BY id FOR UPDATE', [tuple(self.ids)])
        self.invalidate_recordset()

    def _check_overlap(self):
        for rec in self:
            # Serialize submissions for one employee, including concurrent requests.
            self.env.cr.execute('SELECT id FROM hr_employee WHERE id = %s FOR UPDATE', [rec.employee_id.id])
            domain = [('id', '!=', rec.id), ('employee_id', '=', rec.employee_id.id),
                      ('state', 'in', ['supervisor', 'manager', 'approved'])]
            if self.env['hr.leave'].sudo().search_count([
                ('employee_id', '=', rec.employee_id.id), ('state', '=', 'validate'),
                ('holiday_status_id.split_day_night', '=', True),
                ('date_from', '<', rec.date_stop), ('date_to', '>', rec.date_start),
            ], limit=1):
                raise ValidationError(_('الفترة محسوبة بالفعل في طلب إضافي قديم من الإجازات.'))
            for other in self.sudo().search(domain):
                overlap = rec.date_start < other.date_stop and rec.date_stop > other.date_start
                same_day = bool(set(d for d, _, _ in rec._daily_segments()) & set(d for d, _, _ in other._daily_segments()))
                if overlap or (same_day and 'holiday_day' in (rec.kind, other.kind)):
                    raise ValidationError(_('يوجد طلب إضافي متداخل، أو تشغيل يوم عطلة محسوب عن نفس اليوم.'))

    def action_submit(self):
        self._lock()
        self._check_manager()
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('يمكن إرسال المسودة فقط.'))
            if not rec.sudo().department_id.supervisor_id.user_id or not rec.sudo().department_id.manager_id.user_id:
                raise UserError(_('يجب تحديد مشرف ورئيس للقسم وربط كل منهما بمستخدم.'))
            rec._check_overlap()
            super(OvertimeRequest, rec).write({'state': 'supervisor'})
        return True

    def action_approve(self):
        self._lock()
        for rec in self:
            role = rec._approval_role()
            if not role:
                raise AccessError(_('الطلب ليس في مرحلة موافقتك أو لا تملك صلاحية اعتماده.'))
            vals = {role + '_user_id': self.env.uid, role + '_approved_at': fields.Datetime.now(),
                    'state': 'manager' if role == 'supervisor' else 'hr'}
            if role == 'manager':
                rec._check_overlap()
                rec._check_finalized_payroll()
            super(OvertimeRequest, rec).write(vals)
        return True

    def action_hr_approve(self):
        self._lock()
        for rec in self:
            if rec.state != 'hr' or not rec._is_hr_approver():
                raise AccessError(_('الطلب ليس في مرحلة اعتماد الموارد البشرية أو لا تملك الصلاحية.'))
            rec._check_overlap()
            rec._check_finalized_payroll()
            rec._create_work_entries()
            super(OvertimeRequest, rec).write({
                'hr_user_id': self.env.uid,
                'hr_approved_at': fields.Datetime.now(),
                'state': 'approved',
            })
        return True

    def action_refuse(self):
        self._lock()
        for rec in self:
            if not rec._approval_role():
                raise AccessError(_('لا يمكنك رفض هذا الطلب في مرحلته الحالية.'))
            super(OvertimeRequest, rec).write({'state': 'refused'})
        return True

    def action_cancel(self):
        self._lock()
        self._check_manager()
        for rec in self:
            if rec.state not in ('draft', 'supervisor', 'manager', 'hr', 'approved'):
                raise UserError(_('لا يمكن إلغاء هذا الطلب.'))
            rec._check_finalized_payroll()
            entries = rec.sudo().work_entry_ids
            if any(entry.state == 'validated' for entry in entries):
                raise UserError(_('الطلب مستخدم في راتب معتمد؛ أعد الراتب إلى المسودة أولاً.'))
            entries._cancel_overtime_entries()
            super(OvertimeRequest, rec).write({'state': 'cancelled'})
        return True

    def _check_finalized_payroll(self):
        self.ensure_one()
        dates = [day for day, _, _ in self._daily_segments()]
        if self.env['hr.payslip'].sudo().search_count([
            ('employee_id', '=', self.employee_id.id), ('state', 'in', ['validated', 'paid']),
            ('date_from', '<=', max(dates)), ('date_to', '>=', min(dates)),
        ], limit=1):
            raise UserError(_('الفترة لها راتب معتمد؛ أعد الراتب إلى المسودة قبل تغيير الإضافي.'))

    def _hour_parts(self, left, right):
        company = self.sudo().company_id
        day_start, day_end = company.overtime_day_start, company.overtime_day_end
        # Localize clock boundaries independently so DST days retain elapsed hours.
        zone = pytz.timezone(self.timezone)
        start = zone.localize(datetime.combine(left.date(), time.min) + timedelta(hours=day_start))
        end = zone.localize(datetime.combine(left.date(), time.min) + timedelta(hours=day_end))
        day = max(0, (min(right, end) - max(left, start)).total_seconds() / 3600)
        total = (right - left).total_seconds() / 3600
        return [('day', day), ('night', total - day)]

    def _create_work_entries(self):
        self.ensure_one()
        rec = self.sudo()
        if rec.work_entry_ids:
            raise UserError(_('تم إنشاء سجلات العمل لهذا الطلب بالفعل.'))
        if rec.kind != 'holiday_day' and not rec.company_id.overtime_policy_confirmed:
            raise UserError(_('يجب تأكيد إعدادات فترات ومعاملات العمل الإضافي في الشركة أولاً.'))
        values = []
        mission_regular_remaining = 8.0
        for day, left, right in rec._daily_segments():
            version = rec.employee_id._get_version(day)
            if not version or not version.contract_date_start or version.contract_date_start > day or (version.contract_date_end and version.contract_date_end < day):
                raise UserError(_('لا يوجد عقد ساري للموظف بتاريخ %s.', day))
            hours = (right - left).total_seconds() / 3600
            if rec.kind == 'hours':
                parts = rec._hour_parts(left, right)
            elif rec.kind == 'mission':
                regular_hours = min(mission_regular_remaining, hours)
                mission_regular_remaining -= regular_hours
                parts = [('mission_regular', regular_hours)]
                if regular_hours < hours:
                    excess_start = left + timedelta(hours=regular_hours)
                    parts += rec._hour_parts(excess_start, right)
            else:
                parts = [(rec.kind, hours)]
            for category, duration in parts:
                if duration <= 0:
                    continue
                multiplier = {
                    'mission_regular': 1.0,
                    'day': 1.35,
                    'night': 1.70,
                    'holiday_day': 2,
                    'holiday_hours': rec.company_id.overtime_holiday_multiplier,
                }[category]
                values.append({'employee_id': rec.employee_id.id, 'version_id': version.id,
                    'company_id': rec.company_id.id, 'date': day, 'duration': duration,
                    'work_entry_type_id': self.env.ref('thamar_holiday_overtime.work_entry_' + category).id,
                    'overtime_request_id': rec.id, 'overtime_category': category,
                    'overtime_multiplier': multiplier, 'name': rec.name})
        self.env['hr.work.entry'].sudo()._create_overtime_entries(values)
