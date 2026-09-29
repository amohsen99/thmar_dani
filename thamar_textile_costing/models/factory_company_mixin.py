from odoo import fields, models


class CompanyMixin(models.AbstractModel):
    _name = 'factory.company.mixin'
    _description = 'بيانات شركة المصنع'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', string='الشركة', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string='العملة')
