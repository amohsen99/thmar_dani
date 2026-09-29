from odoo import fields, models


class Fabric(models.Model):
    _name = 'factory.fabric'
    _inherit = 'factory.company.mixin'
    _description = 'مواصفات القماش'
    name = fields.Char('اسم القماش', required=True)
    product_id = fields.Many2one('product.product', string='الصنف', check_company=True)
    meters_per_kg = fields.Float('متر لكل كجم', digits=(16, 6), required=True, default=1)
    speed_ids = fields.One2many('factory.fabric.speed', 'fabric_id', string='سرعات التشغيل')
    _factor_valid = models.Constraint('CHECK(meters_per_kg > 0)', 'معامل التحويل يجب أن يكون أكبر من صفر.')
