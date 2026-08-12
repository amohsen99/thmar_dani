# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    secondary_uom_id = fields.Many2one(
        'uom.uom', compute='_compute_secondary_uom_id',
        string="Secondary UOM", store=True)
    secondary_quantity = fields.Float(
        'Secondary Qty', digits='Product Unit of Measure', store=True,
        help="Demand quantity in secondary UOM (e.g. bolts). Entered independently.")
    secondary_done_qty = fields.Float(
        'Secondary Quantity Done', digits='Product Unit of Measure', store=True,
        help="Actual done quantity in secondary UOM. Enter manually.")

    @api.depends('product_id')
    def _compute_secondary_uom_id(self):
        for move in self:
            if move.product_id.secondary_uom:
                move.secondary_uom_id = move.product_id.secondary_uom_id
            else:
                move.secondary_uom_id = False

    def _action_done(self, cancel_backorder=False):
        """Override to update quant secondary_quantity when moves are validated."""
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for move in res:
            if not move.product_id.secondary_uom or not move.secondary_done_qty:
                continue
            self._update_secondary_quant(move)
        return res

    def _update_secondary_quant(self, move):
        """Update secondary_quantity on quants based on move direction."""
        for move_line in move.move_line_ids:
            # Destination quant — add secondary qty
            if move_line.location_dest_id.usage == 'internal':
                quant = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', move.product_id.id),
                    ('location_id', '=', move_line.location_dest_id.id),
                    ('lot_id', '=', move_line.lot_id.id if move_line.lot_id else False),
                    ('package_id', '=', move_line.result_package_id.id if move_line.result_package_id else False),
                    ('owner_id', '=', move_line.owner_id.id if move_line.owner_id else False),
                ], limit=1)
                if quant:
                    # Proportionally distribute secondary qty across move lines
                    if move.quantity and move_line.quantity:
                        line_secondary = (move_line.quantity / move.quantity) * move.secondary_done_qty
                    else:
                        line_secondary = move.secondary_done_qty
                    quant.sudo().write({
                        'secondary_quantity': quant.secondary_quantity + line_secondary,
                    })

            # Source quant — subtract secondary qty
            if move_line.location_id.usage == 'internal':
                quant = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', move.product_id.id),
                    ('location_id', '=', move_line.location_id.id),
                    ('lot_id', '=', move_line.lot_id.id if move_line.lot_id else False),
                    ('package_id', '=', move_line.package_id.id if move_line.package_id else False),
                    ('owner_id', '=', move_line.owner_id.id if move_line.owner_id else False),
                ], limit=1)
                if quant:
                    if move.quantity and move_line.quantity:
                        line_secondary = (move_line.quantity / move.quantity) * move.secondary_done_qty
                    else:
                        line_secondary = move.secondary_done_qty
                    quant.sudo().write({
                        'secondary_quantity': quant.secondary_quantity - line_secondary,
                    })

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        res = super(StockMove, self)._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if res:
            res.update({
                'secondary_uom_id': self.secondary_uom_id and self.secondary_uom_id.id or False,
            })
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    secondary_uom_id = fields.Many2one(
        'uom.uom', string="Secondary UOM",
        compute="_compute_secondary_uom_id", store=True)
    secondary_quantity = fields.Float(
        "Secondary Qty", digits='Product Unit of Measure', store=True,
        help="Secondary quantity for this move line. Entered independently.")
    secondary_done_qty = fields.Float(
        "Secondary Done Qty", digits='Product Unit of Measure',
        help="Actual secondary quantity done for this move line.")

    @api.depends('product_id', 'product_id.secondary_uom_id')
    def _compute_secondary_uom_id(self):
        for move_line in self:
            if move_line.product_id.secondary_uom:
                move_line.secondary_uom_id = move_line.product_id.secondary_uom_id
            else:
                move_line.secondary_uom_id = False