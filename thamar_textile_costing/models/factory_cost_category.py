from odoo import fields, models


class CostCategory(models.Model):
    _name = 'factory.cost.category'
    _description = 'بند تكلفة الساعة'
    name = fields.Char('البند', required=True)
    code = fields.Char('الكود', required=True)
    _code_unique = models.Constraint('unique(code)', 'كود بند التكلفة مكرر.')
