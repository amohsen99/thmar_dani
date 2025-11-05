from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    manager_id = fields.Many2one('res.users', string='Warehouse Manager')
    keeper_id = fields.Many2one('res.users', string='Warehouse Keeper')
