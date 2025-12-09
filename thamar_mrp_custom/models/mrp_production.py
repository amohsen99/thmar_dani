# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        help='Customer for this manufacturing order'
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        help='Related sale order for this manufacturing order'
    )

