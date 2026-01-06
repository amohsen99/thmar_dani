# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Check if product is fabric
    is_fabric = fields.Boolean(
        string='Is Fabric',
        related='product_id.is_fabric',
        store=True,
    )

    # Expected pieces (SECONDARY - auto-calculated)
    fabric_pieces = fields.Float(
        string='عدد الأتواب المتوقع',
        digits=(16, 2),
        compute='_compute_fabric_pieces',
        inverse='_inverse_fabric_pieces',
        store=True,
    )

    # Expected meters (SECONDARY - auto-calculated)
    fabric_expected_meters = fields.Float(
        string='إجمالي الأمتار المتوقع',
        digits=(16, 2),
        compute='_compute_fabric_expected_meters',
        inverse='_inverse_fabric_expected_meters',
        store=True,
    )

    fabric_pieces_manual = fields.Boolean(default=False)
    fabric_meters_manual = fields.Boolean(default=False)

    # Actual produced pieces
    fabric_produced_pieces = fields.Float(
        string='عدد الأتواب المُنتَج',
        digits=(16, 2),
    )

    # Actual produced meters
    fabric_produced_meters = fields.Float(
        string='إجمالي الأمتار المُنتَج',
        digits=(16, 2),
    )

    # Average weight per piece (computed)
    fabric_avg_weight = fields.Float(
        string='متوسط وزن التوب',
        compute='_compute_fabric_avg_weight',
        digits=(16, 3),
    )

    @api.depends('product_qty', 'product_id.fabric_approx_weight', 'fabric_pieces_manual')
    def _compute_fabric_pieces(self):
        for mo in self:
            if not mo.fabric_pieces_manual:
                if mo.is_fabric and mo.product_qty and mo.product_id.fabric_approx_weight:
                    mo.fabric_pieces = round(mo.product_qty / mo.product_id.fabric_approx_weight, 2)
                else:
                    mo.fabric_pieces = 0.0

    def _inverse_fabric_pieces(self):
        for mo in self:
            mo.fabric_pieces_manual = True

    @api.depends('fabric_pieces', 'product_id.fabric_approx_meters', 'fabric_meters_manual')
    def _compute_fabric_expected_meters(self):
        for mo in self:
            if not mo.fabric_meters_manual:
                if mo.is_fabric and mo.fabric_pieces and mo.product_id.fabric_approx_meters:
                    mo.fabric_expected_meters = mo.fabric_pieces * mo.product_id.fabric_approx_meters
                else:
                    mo.fabric_expected_meters = 0.0

    def _inverse_fabric_expected_meters(self):
        for mo in self:
            mo.fabric_meters_manual = True

    @api.depends('qty_producing', 'fabric_produced_pieces')
    def _compute_fabric_avg_weight(self):
        for mo in self:
            if mo.is_fabric and mo.fabric_produced_pieces:
                mo.fabric_avg_weight = mo.qty_producing / mo.fabric_produced_pieces
            else:
                mo.fabric_avg_weight = 0.0

