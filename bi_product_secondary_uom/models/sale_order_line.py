# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round as round


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    secondary_uom_id = fields.Many2one(
        'uom.uom', compute='_compute_secondary_uom_id',
        string="Secondary UOM", store=True, precompute=True)
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

    def _prepare_procurement_values(self, group_id=False):
        """Pass secondary qty to the stock move created from SO."""
        values = super()._prepare_procurement_values(group_id=group_id)
        values['secondary_uom_id'] = self.secondary_uom_id.id
        values['secondary_quantity'] = self.secondary_quantity
        return values
