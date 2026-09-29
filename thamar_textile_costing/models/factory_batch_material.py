from odoo import fields, models


class BatchMaterial(models.Model):
    _name = 'factory.batch.material'
    _inherit = 'factory.batch.child'
    _description = 'أصباغ ومواد التشغيلة'
    name = fields.Char('البيان', required=True)
    kind = fields.Selection([('dye', 'أصباغ'), ('dye_material', 'مواد صباغة'), ('finish_material', 'مواد تجهيز')], default='dye', required=True, string='التصنيف')
    amount = fields.Monetary('القيمة', required=True)
    _amount_valid = models.Constraint('CHECK(amount >= 0)', 'قيمة المواد لا تكون سالبة.')
