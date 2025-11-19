from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    manager_ids = fields.Many2many(
        'res.users',
        'warehouse_manager_rel',
        'warehouse_id',
        'user_id',
        string='Warehouse Managers'
    )
    keeper_ids = fields.Many2many(
        'res.users',
        'warehouse_keeper_rel',
        'warehouse_id',
        'user_id',
        string='Warehouse Keepers'
    )
