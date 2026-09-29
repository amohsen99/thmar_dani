from odoo import api, fields, models
from odoo.exceptions import UserError


class Batch(models.Model):
    _name = 'factory.dyeing.batch'
    _inherit = 'factory.company.mixin'
    _description = 'تشغيلة صباغة وتجهيز'
    _order = 'date desc, id desc'

    name = fields.Char('رقم التشغيلة', required=True, default='جديد', copy=False)
    job_id = fields.Many2one('factory.job', string='أمر الشغل', required=True, check_company=True, ondelete='restrict')
    partner_id = fields.Many2one(related='job_id.partner_id', store=True, string='العميل')
    fabric_id = fields.Many2one(related='job_id.fabric_id', store=True, string='القماش')
    date = fields.Date('تاريخ التشغيل والتسعير', required=True, default=fields.Date.context_today, index=True)
    color_id = fields.Many2one('factory.color', string='اللون', required=True)
    raw_kg = fields.Float('الخام كجم')
    meters_per_kg = fields.Float('معامل متر/كجم المستخدم', required=True, default=1, digits=(16, 6))
    raw_meters = fields.Float('الخام متر', compute='_compute_totals', store=True)
    finished_kg = fields.Float('تام أولى كجم')
    finished_meters = fields.Float('تام أولى متر')
    second_kg = fields.Float('درجة ثانية كجم')
    second_meters = fields.Float('درجة ثانية متر')
    waste_kg = fields.Float('فضلات كجم')
    loss_percent = fields.Float('فاقد وزن %', compute='_compute_totals', store=True)
    operation_ids = fields.One2many('factory.batch.operation', 'batch_id', string='مراحل التشغيل', copy=True)
    material_ids = fields.One2many('factory.batch.material', 'batch_id', string='الأصباغ والمواد', copy=True)
    dye_time_cost = fields.Monetary('تكلفة وقت الصباغة', compute='_compute_totals', store=True)
    finish_time_cost = fields.Monetary('تكلفة وقت التجهيز', compute='_compute_totals', store=True)
    material_cost = fields.Monetary('إجمالي الأصباغ والمواد', compute='_compute_totals', store=True)
    extra_percent = fields.Float('إضافة على تكلفة الوقت %')
    extra_reason = fields.Char('سبب الإضافة')
    extra_cost = fields.Monetary('قيمة الإضافة', compute='_compute_totals', store=True)
    total_cost = fields.Monetary('التكلفة النهائية', compute='_compute_totals', store=True)
    cost_per_kg = fields.Monetary('تكلفة كجم أولى', compute='_compute_totals', store=True, aggregator=False)
    cost_per_meter = fields.Monetary('تكلفة متر أولى', compute='_compute_totals', store=True, aggregator=False)
    total_hours = fields.Float('إجمالي ساعات المراحل', compute='_compute_totals', store=True)
    state = fields.Selection([('draft', 'مسودة'), ('approved', 'معتمدة')], string='الحالة', default='draft', readonly=True, required=True, copy=False)
    approved_by = fields.Many2one('res.users', string='اعتمد بواسطة', readonly=True, copy=False)
    approved_at = fields.Datetime('تاريخ الاعتماد', readonly=True, copy=False)
    notes = fields.Text('ملاحظات')
    _quantities_valid = models.Constraint('CHECK(raw_kg >= 0 AND meters_per_kg > 0 AND finished_kg >= 0 AND finished_meters >= 0 AND second_kg >= 0 AND second_meters >= 0 AND waste_kg >= 0 AND extra_percent >= 0)', 'الكميات والنسب لا تكون سالبة ومعامل التحويل أكبر من صفر.')

    @api.onchange('job_id')
    def _onchange_job(self):
        if self.job_id:
            self.meters_per_kg = self.job_id.fabric_id.meters_per_kg

    @api.depends('raw_kg', 'meters_per_kg', 'finished_kg', 'finished_meters', 'second_kg', 'waste_kg', 'extra_percent', 'operation_ids.cost', 'operation_ids.kind', 'operation_ids.hours', 'material_ids.amount')
    def _compute_totals(self):
        for rec in self:
            rec.raw_meters = rec.raw_kg * rec.meters_per_kg
            rec.loss_percent = (rec.raw_kg - rec.finished_kg - rec.second_kg - rec.waste_kg) / rec.raw_kg * 100 if rec.raw_kg else 0
            rec.dye_time_cost = sum(rec.operation_ids.filtered(lambda l: l.kind == 'dye').mapped('cost'))
            rec.finish_time_cost = sum(rec.operation_ids.filtered(lambda l: l.kind == 'finish').mapped('cost'))
            rec.material_cost = sum(rec.material_ids.mapped('amount'))
            rec.total_hours = sum(rec.operation_ids.mapped('hours'))
            time_cost = rec.dye_time_cost + rec.finish_time_cost
            rec.extra_cost = time_cost * rec.extra_percent / 100
            rec.total_cost = time_cost + rec.material_cost + rec.extra_cost
            rec.cost_per_kg = rec.total_cost / rec.finished_kg if rec.finished_kg else 0
            rec.cost_per_meter = rec.total_cost / rec.finished_meters if rec.finished_meters else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('state', 'draft') != 'draft' or vals.get('approved_by') or vals.get('approved_at'):
                raise UserError('استخدم زر اعتماد التكلفة.')
            if vals.get('name', 'جديد') == 'جديد':
                vals['name'] = self.env['ir.sequence'].next_by_code('factory.dyeing.batch') or 'جديد'
            if 'meters_per_kg' not in vals and vals.get('job_id'):
                vals['meters_per_kg'] = self.env['factory.job'].browse(vals['job_id']).fabric_id.meters_per_kg
        return super().create(vals_list)

    def write(self, vals):
        if any(r.state == 'approved' for r in self) or {'state', 'approved_by', 'approved_at'} & set(vals):
            raise UserError('التكلفة المعتمدة مقفلة. استخدم نسخة جديدة للتصحيح.')
        return super().write(vals)

    def unlink(self):
        if any(r.state == 'approved' for r in self):
            raise UserError('لا يمكن حذف تشغيلة معتمدة.')
        return super().unlink()

    def action_approve(self):
        if not self.env.su and not self.env.user.has_group('thamar_textile_costing.group_manager'):
            raise UserError('اعتماد التكلفة متاح لمدير التكاليف فقط.')
        for rec in self:
            if rec.state != 'draft':
                raise UserError('التشغيلة معتمدة بالفعل.')
            if not rec.operation_ids or rec.raw_kg <= 0 or rec.finished_kg <= 0 or rec.finished_meters <= 0:
                raise UserError('سجل مراحل التشغيل والخام وكميات التام بالكيلو والمتر قبل الاعتماد.')
            if rec.extra_percent and not rec.extra_reason:
                raise UserError('وضح سبب الإضافة على تكلفة الوقت.')
            for line in rec.operation_ids:
                line._check_duration()
                if line.hours <= 0:
                    raise UserError('مدة كل مرحلة يجب أن تكون أكبر من صفر.')
                rate = line._find_rate()
                if not rate:
                    raise UserError('لا يوجد سعر ساعة معتمد للماكينة %s في شهر %s.' % (line.machine_id.name, rec.date.strftime('%Y-%m')))
                line.write({'rate_id': rate.id, 'snapshot_rate': rate.hourly_rate, 'kind': line.operation_id.kind})
            super(Batch, rec).write({'state': 'approved', 'approved_by': self.env.uid, 'approved_at': fields.Datetime.now()})
        return True

    def action_refresh_rates(self):
        for rec in self:
            if rec.state == 'draft':
                for line in rec.operation_ids:
                    line.rate_id = line._find_rate()
