from odoo import fields, models


class Center(models.Model):
    _name = 'factory.cost.center'
    _inherit = 'factory.company.mixin'
    _description = 'قسم ومركز تكلفة'

    name = fields.Char('الاسم', required=True)
    code = fields.Char('الكود')
    kind = fields.Selection([('dye', 'صباغة'), ('finish', 'تجهيز'), ('print', 'طباعة'), ('weave', 'نسيج'), ('service', 'خدمات')], required=True, default='dye', string='النوع')
    active = fields.Boolean(default=True)
