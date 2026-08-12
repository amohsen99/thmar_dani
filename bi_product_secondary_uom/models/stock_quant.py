# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    secondary_uom_id = fields.Many2one(
        'uom.uom', compute='_compute_secondary_uom_id',
        string="Secondary UOM", store=True)
    secondary_quantity = fields.Float(
        'Secondary Qty', digits='Product Unit of Measure',
        help="Independent secondary quantity (e.g. number of bolts/pieces). "
             "Updated automatically from validated stock moves.")

    @api.depends('product_id', 'product_id.secondary_uom_id')
    def _compute_secondary_uom_id(self):
        for quant in self:
            if quant.product_id.secondary_uom:
                quant.secondary_uom_id = quant.product_id.secondary_uom_id
            else:
                quant.secondary_uom_id = False
