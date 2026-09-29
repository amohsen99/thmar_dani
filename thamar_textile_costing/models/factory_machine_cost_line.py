from odoo import api, fields, models
from odoo.exceptions import UserError


class RateLine(models.Model):
    _name = 'factory.machine.cost.line'
    _description = 'تفصيل تكلفة الساعة'
    _check_company_auto = True
    rate_id = fields.Many2one('factory.machine.cost.rate', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='rate_id.company_id', store=True)
    currency_id = fields.Many2one(related='rate_id.currency_id')
    category_id = fields.Many2one('factory.cost.category', string='بند التكلفة', required=True)
    method = fields.Selection([('fixed', 'مبلغ لكل ساعة'), ('usage', 'استهلاك × سعر'), ('allocated', 'مصروف فترة موزع')], default='fixed', required=True, string='طريقة الحساب')
    fixed_amount = fields.Monetary('مبلغ/ساعة')
    consumption = fields.Float('استهلاك/ساعة')
    unit_label = fields.Char('وحدة الاستهلاك')
    unit_price = fields.Float('سعر الوحدة بعملة الشركة', digits=(16, 6))
    period_amount = fields.Monetary('مصروف الفترة')
    allocation_percent = fields.Float('نصيب الماكينة %', default=100)
    period_hours = fields.Float('ساعات الفترة', default=1)
    amount = fields.Monetary('تكلفة/ساعة', compute='_compute_amount', store=True)
    notes = fields.Char('مصدر وأساس التوزيع')
    _values_valid = models.Constraint('CHECK(fixed_amount >= 0 AND consumption >= 0 AND unit_price >= 0 AND period_amount >= 0 AND allocation_percent >= 0 AND allocation_percent <= 100 AND period_hours > 0)', 'راجع قيم التكلفة ونسبة التوزيع وساعات الفترة.')

    @api.depends('method', 'fixed_amount', 'consumption', 'unit_price', 'period_amount', 'allocation_percent', 'period_hours')
    def _compute_amount(self):
        for rec in self:
            if rec.method == 'usage':
                rec.amount = rec.consumption * rec.unit_price
            elif rec.method == 'allocated':
                rec.amount = rec.period_amount * rec.allocation_percent / 100 / rec.period_hours if rec.period_hours else 0
            else:
                rec.amount = rec.fixed_amount

    @api.model_create_multi
    def create(self, vals_list):
        rates = self.env['factory.machine.cost.rate'].browse([v.get('rate_id') for v in vals_list if v.get('rate_id')])
        if any(r.state == 'approved' for r in rates):
            raise UserError('السعر معتمد؛ أعده لمسودة أولاً.')
        return super().create(vals_list)

    def write(self, vals):
        rates = self.mapped('rate_id') | self.env['factory.machine.cost.rate'].browse(vals.get('rate_id', []))
        if any(r.state == 'approved' for r in rates):
            raise UserError('لا يمكن تغيير تفاصيل سعر معتمد.')
        return super().write(vals)

    def unlink(self):
        if any(r.rate_id.state == 'approved' for r in self):
            raise UserError('لا يمكن حذف تفاصيل سعر معتمد.')
        return super().unlink()
