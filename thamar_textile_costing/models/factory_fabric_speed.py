from odoo import fields, models


class Speed(models.Model):
    _name = 'factory.fabric.speed'
    _description = 'سرعة مرحلة لصنف'
    _check_company_auto = True
    fabric_id = fields.Many2one('factory.fabric', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='fabric_id.company_id', store=True)
    operation_id = fields.Many2one('factory.operation', string='المرحلة', required=True)
    machine_id = fields.Many2one('factory.machine', string='الماكينة', required=True, check_company=True)
    meters_per_minute = fields.Float('السرعة متر/دقيقة', required=True)
    _speed_valid = models.Constraint('CHECK(meters_per_minute > 0)', 'السرعة يجب أن تكون أكبر من صفر.')
    _speed_unique = models.Constraint('unique(fabric_id, operation_id, machine_id)', 'سرعة المرحلة والماكينة مسجلة بالفعل للصنف.')
