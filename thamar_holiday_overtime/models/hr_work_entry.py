from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    overtime_request_id = fields.Many2one('thamar.overtime.request', readonly=True, index=True, copy=False, ondelete='restrict')
    overtime_category = fields.Selection([
        ('mission_regular', 'مأمورية بسعر عادي'),
        ('day', 'نهاري'),
        ('night', 'مسائي'),
        ('holiday_day', 'يوم عطلة'),
        ('holiday_hours', 'ساعات عطلات'),
    ], readonly=True, copy=False)
    overtime_multiplier = fields.Float(readonly=True, copy=False)

    @api.model
    def _create_overtime_entries(self, values):
        return super(HrWorkEntry, self).create(values)

    @api.model_create_multi
    def create(self, vals_list):
        if any(set(vals) & {'overtime_request_id', 'overtime_category', 'overtime_multiplier'} for vals in vals_list):
            raise AccessError(_('يتم إنشاء سجلات الإضافي من الطلب المعتمد فقط.'))
        return super().create(vals_list)

    def write(self, vals):
        linked = self.filtered('overtime_request_id')
        if linked and self.env.context.get('thamar_overtime_generation') and vals.get('active') is False and all(value is False for value in vals.values()):
            return super(HrWorkEntry, self - linked).write(vals)
        allowed = {'state'}
        if vals.get('leave_id', True) is False:
            allowed.add('leave_id')  # Core conflict checks clear this on attendance entries.
        if set(vals) & {'overtime_request_id', 'overtime_category', 'overtime_multiplier'} or (linked and set(vals) - allowed):
            raise AccessError(_('عدل العمل الإضافي من الطلب المرتبط به.'))
        if linked and vals.get('state') == 'cancelled':
            raise AccessError(_('ألغِ العمل الإضافي من الطلب المرتبط به.'))
        return super().write(vals)

    def _cancel_overtime_entries(self):
        return super(HrWorkEntry, self).write({'state': 'cancelled', 'active': False})

    def unlink(self):
        if self.filtered('overtime_request_id'):
            raise AccessError(_('لا يمكن حذف سجل إضافي مرتبط بطلب.'))
        return super().unlink()


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _generate_work_entries(self, date_start, date_stop, force=False):
        return super(HrVersion, self.with_context(thamar_overtime_generation=True))._generate_work_entries(date_start, date_stop, force=force)
