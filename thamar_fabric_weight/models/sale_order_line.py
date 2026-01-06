# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Check if product is fabric
    is_fabric = fields.Boolean(
        string='Is Fabric',
        related='product_id.is_fabric',
        store=True,
    )

    # Number of pieces (SECONDARY - auto-calculated, but editable)
    fabric_pieces = fields.Float(
        string='عدد الأتواب',
        digits=(16, 2),
        compute='_compute_fabric_pieces',
        inverse='_inverse_fabric_pieces',
        store=True,
        help='Number of pieces - calculated from weight, but can be manually adjusted'
    )

    # Flag to track if pieces was manually edited
    fabric_pieces_manual = fields.Boolean(
        string='Manual Pieces',
        default=False,
    )

    # Total meters (SECONDARY - auto-calculated, but editable)
    fabric_total_meters = fields.Float(
        string='إجمالي الأمتار',
        digits=(16, 2),
        compute='_compute_fabric_meters',
        inverse='_inverse_fabric_meters',
        store=True,
        help='Total meters - calculated from pieces, but can be manually adjusted'
    )

    # Flag to track if meters was manually edited
    fabric_meters_manual = fields.Boolean(
        string='Manual Meters',
        default=False,
    )

    # Average weight per piece (computed)
    fabric_avg_weight = fields.Float(
        string='متوسط وزن التوب',
        compute='_compute_fabric_avg_weight',
        digits=(16, 3),
    )

    @api.depends('product_uom_qty', 'product_id.fabric_approx_weight', 'fabric_pieces_manual')
    def _compute_fabric_pieces(self):
        for line in self:
            if not line.fabric_pieces_manual:
                if line.is_fabric and line.product_uom_qty and line.product_id.fabric_approx_weight:
                    line.fabric_pieces = round(line.product_uom_qty / line.product_id.fabric_approx_weight, 2)
                else:
                    line.fabric_pieces = 0.0

    def _inverse_fabric_pieces(self):
        """Mark as manually edited when user changes pieces"""
        for line in self:
            line.fabric_pieces_manual = True

    @api.depends('fabric_pieces', 'product_id.fabric_approx_meters', 'fabric_meters_manual')
    def _compute_fabric_meters(self):
        for line in self:
            if not line.fabric_meters_manual:
                if line.is_fabric and line.fabric_pieces and line.product_id.fabric_approx_meters:
                    line.fabric_total_meters = line.fabric_pieces * line.product_id.fabric_approx_meters
                else:
                    line.fabric_total_meters = 0.0

    def _inverse_fabric_meters(self):
        for line in self:
            line.fabric_meters_manual = True

    @api.depends('product_uom_qty', 'fabric_pieces')
    def _compute_fabric_avg_weight(self):
        for line in self:
            if line.is_fabric and line.fabric_pieces:
                line.fabric_avg_weight = line.product_uom_qty / line.fabric_pieces
            else:
                line.fabric_avg_weight = 0.0

    @api.onchange('product_uom_qty')
    def _onchange_fabric_weight(self):
        """Reset manual flag when standard quantity (weight) changes"""
        if self.is_fabric:
            self.fabric_pieces_manual = False
            self.fabric_meters_manual = False

