from odoo import models

class StockMove(models.Model):
    _inherit = 'stock.move'
    # Access control handled by record rules
    pass
