# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    secondary_uom_id = fields.Many2one(
        'uom.uom', compute='_compute_secondary_uom_id',
        string="Secondary UOM", store=True)
    secondary_quantity = fields.Float(
        'Secondary Qty', digits='Product Unit of Measure',
        store=True,
        help="Enter the secondary quantity independently (e.g. number of bolts).")

    @api.depends('product_id')
    def _compute_secondary_uom_id(self):
        for order in self:
            if order.product_id.secondary_uom:
                order.secondary_uom_id = order.product_id.secondary_uom_id
            else:
                order.secondary_uom_id = False

    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        for re in res:
            re['secondary_uom_id'] = self.secondary_uom_id.id
            re['secondary_quantity'] = self.secondary_quantity
        return res
