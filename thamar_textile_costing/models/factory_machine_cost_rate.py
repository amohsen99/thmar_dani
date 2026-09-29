from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class Rate(models.Model):
    _name = 'factory.machine.cost.rate'
    _inherit = 'factory.company.mixin'
    _description = 'تكلفة ساعة الماكينة الشهرية'
    _rec_name = 'display_label'
    _order = 'month desc, machine_id'

    display_label = fields.Char(compute='_compute_label', store=True)
    machine_id = fields.Many2one('factory.machine', string='الماكينة', required=True, check_company=True, ondelete='restrict')
    month = fields.Date('الشهر (أول يوم)', required=True, default=lambda self: fields.Date.context_today(self).replace(day=1), index=True)
    method = fields.Selection([('manual', 'سعر ساعة مباشر'), ('detail', 'من تفاصيل التكلفة')], default='manual', required=True, string='طريقة التسعير')
    manual_rate = fields.Monetary('سعر الساعة المباشر')
    line_ids = fields.One2many('factory.machine.cost.line', 'rate_id', string='تفاصيل الساعة')
    base_rate = fields.Monetary('قبل عدم الاستغلال', compute='_compute_amount', store=True)
    idle_percent = fields.Float('نسبة إضافة عدم الاستغلال %')
    hourly_rate = fields.Monetary('تكلفة الساعة النهائية', compute='_compute_amount', store=True)
    state = fields.Selection([('draft', 'مسودة'), ('approved', 'معتمد')], default='draft', required=True, readonly=True, copy=False, string='الحالة')
    notes = fields.Text('ملاحظات ومصدر السعر')
    _month_unique = models.Constraint('unique(company_id, machine_id, month)', 'يوجد سعر لهذه الماكينة في نفس الشهر.')
    _amount_valid = models.Constraint('CHECK(manual_rate >= 0 AND idle_percent >= 0)', 'الأسعار والنسب لا تكون سالبة.')

    @api.depends('machine_id.name', 'month')
    def _compute_label(self):
        for rec in self:
            rec.display_label = '%s / %s' % (rec.machine_id.name or '', rec.month or '')

    @api.depends('method', 'manual_rate', 'line_ids.amount', 'idle_percent')
    def _compute_amount(self):
        for rec in self:
            rec.base_rate = rec.manual_rate if rec.method == 'manual' else sum(rec.line_ids.mapped('amount'))
            rec.hourly_rate = rec.base_rate * (1 + rec.idle_percent / 100)

    @api.constrains('month')
    def _check_month(self):
        for rec in self:
            if rec.month.day != 1:
                raise ValidationError('سجل الشهر بأول يوم فيه، مثال 2026-09-01.')

    @api.model_create_multi
    def create(self, vals_list):
        if any(v.get('state', 'draft') != 'draft' for v in vals_list):
            raise UserError('استخدم زر اعتماد السعر.')
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals:
            raise UserError('استخدم أزرار اعتماد السعر وإعادة المسودة.')
        if any(r.state == 'approved' for r in self):
            raise UserError('أعد السعر إلى مسودة قبل تعديله. التشغيلات المعتمدة تحتفظ بسعرها.')
        return super().write(vals)

    def action_approve(self):
        for rec in self:
            if rec.method == 'detail' and not rec.line_ids:
                raise UserError('أضف تفاصيل تكلفة الساعة أولاً.')
        return super(Rate, self).write({'state': 'approved'})

    def action_draft(self):
        return super(Rate, self).write({'state': 'draft'})
