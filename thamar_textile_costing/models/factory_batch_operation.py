from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BatchOperation(models.Model):
    _name = 'factory.batch.operation'
    _inherit = 'factory.batch.child'
    _description = 'مرحلة تشغيل التشغيلة'
    _order = 'sequence, id'
    sequence = fields.Integer('الترتيب', default=10)
    operation_id = fields.Many2one('factory.operation', string='المرحلة', required=True, ondelete='restrict')
    kind = fields.Selection([('dye', 'صباغة'), ('finish', 'تجهيز')], string='التصنيف المستخدم', compute='_compute_kind', store=True, precompute=True, readonly=False, required=True)
    machine_id = fields.Many2one('factory.machine', string='الماكينة', required=True, check_company=True, ondelete='restrict')
    duration_method = fields.Selection([('manual', 'ساعات مباشرة'), ('clock', 'بداية ونهاية'), ('speed', 'من السرعة')], string='حساب الزمن', default='manual', required=True)
    manual_hours = fields.Float('ساعات التشغيل')
    start_at = fields.Datetime('البداية')
    end_at = fields.Datetime('النهاية')
    processed_meters = fields.Float('الأمتار المعالجة')
    meters_per_minute = fields.Float('متر/دقيقة')
    hours = fields.Float('المدة بالساعات', compute='_compute_hours', store=True)
    rate_id = fields.Many2one('factory.machine.cost.rate', string='سعر الشهر', compute='_compute_rate', store=True, readonly=False, check_company=True, ondelete='restrict', copy=False)
    snapshot_rate = fields.Monetary('سعر الساعة المثبت', readonly=True, copy=False)
    hourly_rate = fields.Monetary('تكلفة الساعة', compute='_compute_cost', store=True)
    cost = fields.Monetary('تكلفة المرحلة', compute='_compute_cost', store=True)
    rate_missing = fields.Boolean('السعر ناقص', compute='_compute_cost', store=True)
    notes = fields.Char('ملاحظات')
    _values_valid = models.Constraint('CHECK(manual_hours >= 0 AND processed_meters >= 0 AND meters_per_minute >= 0)', 'قيم الزمن والسرعة والكميات لا تكون سالبة.')

    @api.depends('operation_id')
    def _compute_kind(self):
        for rec in self:
            rec.kind = rec.operation_id.kind

    @api.depends('duration_method', 'manual_hours', 'start_at', 'end_at', 'processed_meters', 'meters_per_minute')
    def _compute_hours(self):
        for rec in self:
            if rec.duration_method == 'clock':
                rec.hours = (rec.end_at - rec.start_at).total_seconds() / 3600 if rec.start_at and rec.end_at else 0
            elif rec.duration_method == 'speed':
                rec.hours = rec.processed_meters / rec.meters_per_minute / 60 if rec.meters_per_minute else 0
            else:
                rec.hours = rec.manual_hours

    @api.constrains('duration_method', 'start_at', 'end_at', 'meters_per_minute', 'batch_id')
    def _check_duration(self):
        for rec in self:
            if rec.duration_method == 'clock':
                if not rec.start_at or not rec.end_at or rec.end_at <= rec.start_at:
                    raise ValidationError('أدخل بداية ونهاية صحيحتين للمرحلة.')
                # Date/month comparison uses the current user's local timezone.
                dates = [fields.Datetime.context_timestamp(rec, t).date() for t in (rec.start_at, rec.end_at)]
                if any(d.replace(day=1) != rec.batch_id.date.replace(day=1) for d in dates):
                    raise ValidationError('بداية ونهاية المرحلة يجب أن تكونا في شهر التشغيلة. افصل التشغيل الممتد لشهر آخر.')
            if rec.duration_method == 'speed' and rec.meters_per_minute <= 0:
                raise ValidationError('أدخل سرعة أكبر من صفر.')

    def _find_rate(self):
        self.ensure_one()
        if not self.machine_id or not self.batch_id.date:
            return self.env['factory.machine.cost.rate']
        return self.env['factory.machine.cost.rate'].search([
            ('company_id', '=', self.batch_id.company_id.id), ('machine_id', '=', self.machine_id.id),
            ('month', '=', self.batch_id.date.replace(day=1)), ('state', '=', 'approved')], limit=1)

    @api.depends('machine_id', 'batch_id.date', 'batch_id.company_id')
    def _compute_rate(self):
        for rec in self:
            if rec.batch_id.state != 'approved':
                rec.rate_id = rec._find_rate()

    @api.depends('hours', 'rate_id', 'rate_id.hourly_rate', 'rate_id.state', 'snapshot_rate', 'batch_id.state')
    def _compute_cost(self):
        for rec in self:
            approved = rec.batch_id.state == 'approved'
            rec.rate_missing = not approved and (not rec.rate_id or rec.rate_id.state != 'approved')
            rec.hourly_rate = rec.snapshot_rate if approved else (rec.rate_id.hourly_rate if not rec.rate_missing else 0)
            rec.cost = rec.hours * rec.hourly_rate

    @api.onchange('operation_id', 'machine_id')
    def _onchange_speed(self):
        if self.batch_id.fabric_id and self.operation_id and self.machine_id:
            speed = self.env['factory.fabric.speed'].search([('fabric_id', '=', self.batch_id.fabric_id.id), ('operation_id', '=', self.operation_id.id), ('machine_id', '=', self.machine_id.id)], limit=1)
            if speed:
                self.meters_per_minute = speed.meters_per_minute
