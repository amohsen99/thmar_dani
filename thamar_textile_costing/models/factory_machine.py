from odoo import fields, models


class Machine(models.Model):
    _name = 'factory.machine'
    _inherit = 'factory.company.mixin'
    _description = 'ماكينة المصنع'

    name = fields.Char('اسم الماكينة', required=True)
    code = fields.Char('الكود', required=True)
    center_id = fields.Many2one('factory.cost.center', string='القسم', required=True, check_company=True)
    min_capacity = fields.Float('أقل حمولة كجم')
    max_capacity = fields.Float('أقصى حمولة كجم')
    active = fields.Boolean(default=True)
    _code_unique = models.Constraint('unique(company_id, code)', 'كود الماكينة مكرر في الشركة.')
    _capacity_valid = models.Constraint('CHECK(min_capacity >= 0 AND max_capacity >= min_capacity)', 'راجع حدود حمولة الماكينة.')
