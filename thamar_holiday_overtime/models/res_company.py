from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    overtime_day_start = fields.Float(string='بداية النهاري', default=6)
    overtime_day_end = fields.Float(string='نهاية النهاري', default=18)
    overtime_holiday_multiplier = fields.Float(string='معامل ساعات العطلات', default=2)
    overtime_policy_confirmed = fields.Boolean(string='تم تأكيد سياسة العمل الإضافي', default=False,
        help='كل الساعات خارج الفترة النهارية تعامل كمسائية. يجب تأكيد الفترات ومعامل العطلات قبل الاعتماد.')

    @api.constrains('overtime_day_start', 'overtime_day_end', 'overtime_holiday_multiplier')
    def _check_overtime_policy(self):
        for company in self:
            if not 0 <= company.overtime_day_start < company.overtime_day_end <= 24:
                raise ValidationError(_('الفترة النهارية يجب أن تكون بين 0 و24 وبداية أقل من النهاية.'))
            if company.overtime_holiday_multiplier <= 0:
                raise ValidationError(_('معامل ساعات العطلات يجب أن يكون موجباً.'))
