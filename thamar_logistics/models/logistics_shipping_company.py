from odoo import models, fields


class LogisticsShippingCompany(models.Model):
    _name = 'logistics.shipping.company'
    _description = 'Shipping Company'
    _order = 'name'

    name = fields.Char(string='Company Name', required=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)
