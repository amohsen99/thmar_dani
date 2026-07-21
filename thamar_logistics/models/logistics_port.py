from odoo import models, fields


class LogisticsPort(models.Model):
    _name = 'logistics.port'
    _description = 'Shipping Port'
    _order = 'name'

    name = fields.Char(string='Port Name', required=True)
    country_id = fields.Many2one('res.country', string='Country')
    code = fields.Char(string='Port Code')
    active = fields.Boolean(default=True)
