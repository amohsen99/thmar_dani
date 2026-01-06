# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

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
    )

    # Total meters (SECONDARY - auto-calculated, but editable)
    fabric_total_meters = fields.Float(
        string='إجمالي الأمتار',
        digits=(16, 2),
        compute='_compute_fabric_meters',
        inverse='_inverse_fabric_meters',
        store=True,
    )

    # Flags to track if quantities were manually edited
    fabric_pieces_manual = fields.Boolean(default=False)
    fabric_meters_manual = fields.Boolean(default=False)

    # Average weight per piece (computed)
    fabric_avg_weight = fields.Float(
        string='متوسط وزن التوب',
        compute='_compute_fabric_avg_weight',
        digits=(16, 3),
    )

    @api.depends('product_uom_qty', 'product_id.fabric_approx_weight', 'fabric_pieces_manual')
    def _compute_fabric_pieces(self):
        for move in self:
            if not move.fabric_pieces_manual:
                if move.is_fabric and move.product_uom_qty and move.product_id.fabric_approx_weight:
                    move.fabric_pieces = round(move.product_uom_qty / move.product_id.fabric_approx_weight, 2)
                else:
                    move.fabric_pieces = 0.0

    def _inverse_fabric_pieces(self):
        for move in self:
            move.fabric_pieces_manual = True

    @api.depends('fabric_pieces', 'product_id.fabric_approx_meters', 'fabric_meters_manual')
    def _compute_fabric_meters(self):
        for move in self:
            if not move.fabric_meters_manual:
                if move.is_fabric and move.fabric_pieces and move.product_id.fabric_approx_meters:
                    move.fabric_total_meters = move.fabric_pieces * move.product_id.fabric_approx_meters
                else:
                    move.fabric_total_meters = 0.0

    def _inverse_fabric_meters(self):
        for move in self:
            move.fabric_meters_manual = True

    @api.depends('product_uom_qty', 'fabric_pieces')
    def _compute_fabric_avg_weight(self):
        for move in self:
            if move.is_fabric and move.fabric_pieces:
                move.fabric_avg_weight = move.product_uom_qty / move.fabric_pieces
            else:
                move.fabric_avg_weight = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        # Copy pieces and meters from sale/purchase order line if available
        for move in moves:
            if move.is_fabric:
                source_line = move.sale_line_id or move.purchase_line_id
                if source_line:
                    move.fabric_pieces = source_line.fabric_pieces
                    move.fabric_pieces_manual = source_line.fabric_pieces_manual
                    move.fabric_total_meters = source_line.fabric_total_meters
                    move.fabric_meters_manual = getattr(source_line, 'fabric_meters_manual', False)
        return moves

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if self.is_fabric:
            # Ensure fabric fields are passed to move line
            # If quantity is not provided, use full move quantity
            qty_to_process = quantity or self.product_uom_qty
            ratio = qty_to_process / self.product_uom_qty if self.product_uom_qty else 1.0
            
            vals['fabric_pieces'] = self.fabric_pieces * ratio
            vals['fabric_total_meters'] = self.fabric_total_meters * ratio
        return vals

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for move in self.filtered(lambda m: m.is_fabric and m.state == 'done'):
            for line in move.move_line_ids:
                if line.state == 'done':
                    # Sync only pieces and meters to quants (weight is handled by Odoo)
                    pieces = line.fabric_pieces or (move.fabric_pieces if len(move.move_line_ids) == 1 else 0.0)
                    meters = line.fabric_total_meters or (move.fabric_total_meters if len(move.move_line_ids) == 1 else 0.0)

                    # Update Source Location (if internal) - subtract
                    if line.location_id.usage == 'internal':
                        self.env['stock.quant']._update_available_quantity(
                            line.product_id, line.location_id, 0.0,
                            lot_id=line.lot_id, package_id=line.package_id, owner_id=line.owner_id,
                            fabric_pieces=-pieces,
                            fabric_meters=-meters
                        )
                    # Update Destination Location (if internal) - add
                    if line.location_dest_id.usage == 'internal':
                        self.env['stock.quant']._update_available_quantity(
                            line.product_id, line.location_dest_id, 0.0,
                            lot_id=line.lot_id, package_id=line.package_id, owner_id=line.owner_id,
                            fabric_pieces=pieces,
                            fabric_meters=meters
                        )
        return res

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_fabric = fields.Boolean(related='product_id.is_fabric', store=True)
    fabric_pieces = fields.Float(string='عدد الأتواب', digits=(16, 2))
    fabric_total_meters = fields.Float(string='إجمالي الأمتار', digits=(16, 2))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'move_id' in vals and not vals.get('fabric_pieces'):
                move = self.env['stock.move'].browse(vals['move_id'])
                if move.is_fabric:
                    # If quantity is provided, use ratio. Otherwise use move totals.
                    qty = vals.get('quantity') or move.product_uom_qty
                    ratio = qty / move.product_uom_qty if move.product_uom_qty else 1.0
                    vals.update({
                        'fabric_pieces': move.fabric_pieces * ratio,
                        'fabric_total_meters': move.fabric_total_meters * ratio,
                    })
        return super().create(vals_list)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

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

    # Check if picking has fabric products
    has_fabric = fields.Boolean(
        string='يحتوي أقمشة',
        compute='_compute_fabric_totals',
        store=True,
    )

    @api.depends('move_ids', 'move_ids.is_fabric', 'move_ids.fabric_pieces',
                 'move_ids.product_uom_qty', 'move_ids.fabric_total_meters')
    def _compute_fabric_totals(self):
        for picking in self:
            fabric_moves = picking.move_ids.filtered(lambda m: m.is_fabric)
            picking.has_fabric = bool(fabric_moves)
            picking.fabric_total_weight = sum(fabric_moves.mapped('product_uom_qty'))
            picking.fabric_total_qty = sum(fabric_moves.mapped('fabric_pieces'))
            picking.fabric_total_meters = sum(fabric_moves.mapped('fabric_total_meters'))

