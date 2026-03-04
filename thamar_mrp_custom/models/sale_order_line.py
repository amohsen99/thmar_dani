# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    
    has_fabric = fields.Boolean('Has Fabric', default=False)

    # Removing custom feature fields and logic as they are no longer synchronized to production
