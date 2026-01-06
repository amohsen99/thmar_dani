# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Total fabric weight (PRIMARY)
    fabric_total_weight = fields.Float(
        string='إجمالي الوزن (كجم)',
        compute='_compute_fabric_totals',
        store=True,
        digits=(16, 3),
    )

    # Total fabric pieces (SECONDARY)
    fabric_total_qty = fields.Float(
        string='إجمالي الأتواب',
        compute='_compute_fabric_totals',
        store=True,
        digits=(16, 2),
    )

    # Total fabric meters (SECONDARY)
    fabric_total_meters = fields.Float(
        string='إجمالي الأمتار',
        compute='_compute_fabric_totals',
        store=True,
        digits=(16, 2),
    )

    # Check if order has fabric products
    has_fabric = fields.Boolean(
        string='يحتوي أقمشة',
        compute='_compute_fabric_totals',
        store=True,
    )

    @api.depends('order_line', 'order_line.is_fabric', 'order_line.fabric_pieces',
                 'order_line.product_qty', 'order_line.fabric_total_meters')
    def _compute_fabric_totals(self):
        for order in self:
            fabric_lines = order.order_line.filtered(lambda l: l.is_fabric)
            order.has_fabric = bool(fabric_lines)
            order.fabric_total_weight = sum(fabric_lines.mapped('product_qty'))
            order.fabric_total_qty = sum(fabric_lines.mapped('fabric_pieces'))
            order.fabric_total_meters = sum(fabric_lines.mapped('fabric_total_meters'))

