from odoo import fields, models


class Color(models.Model):
    _name = 'factory.color'
    _description = 'لون القماش'
    name = fields.Char('اللون', required=True)
    code = fields.Char('الكود')
    active = fields.Boolean(default=True)
