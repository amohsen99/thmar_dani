# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity=False, reserved_quantity=False, lot_id=None, package_id=None, owner_id=None, in_date=None, **kwargs):
        """
        Extend Odoo core method to also update fabric-specific fields.
        """
        fabric_pieces = kwargs.get('fabric_pieces', 0.0)
        fabric_meters = kwargs.get('fabric_meters', 0.0)

        # If core quantities are provided, or NO fabric fields are present, call super
        if (quantity or reserved_quantity) or not (fabric_pieces or fabric_meters):
            return super()._update_available_quantity(
                product_id, location_id, quantity=quantity, 
                reserved_quantity=reserved_quantity,
                lot_id=lot_id, package_id=package_id, 
                owner_id=owner_id, in_date=in_date
            )

        # Handling case where ONLY fabric fields are updated (quantity=0, reserved=0)
        # This bypasses the ValidationError in Odoo core's _update_available_quantity
        quant = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
        if quant:
            quant = quant.try_lock_for_update(allow_referencing=True, limit=1)
            quant.write({
                'fabric_pieces': (quant.fabric_pieces or 0.0) + fabric_pieces,
                'fabric_meters': (quant.fabric_meters or 0.0) + fabric_meters,
            })
        
        # Return expected tuple (available_quantity, in_date)
        return self._get_available_quantity(
            product_id, location_id, lot_id=lot_id, 
            package_id=package_id, owner_id=owner_id, 
            strict=True, allow_negative=True
        ), in_date or fields.Datetime.now()

    # Check if product is fabric
    is_fabric = fields.Boolean(
        string='Is Fabric',
        related='product_id.is_fabric',
        store=True,
    )

    # Number of pieces in this location (SECONDARY)
    fabric_pieces = fields.Float(
        string='عدد الأتواب',
        digits=(16, 2),
        help='Number of pieces in this location'
    )

    # Total meters in this location (SECONDARY)
    fabric_meters = fields.Float(
        string='إجمالي الأمتار',
        digits=(16, 2),
        help='Total meters of fabric in this location'
    )

    # Average weight per piece (computed)
    fabric_avg_weight = fields.Float(
        string='متوسط وزن التوب',
        compute='_compute_fabric_avg_weight',
        digits=(16, 3),
    )

    @api.depends('fabric_pieces', 'quantity')
    def _compute_fabric_avg_weight(self):
        for quant in self:
            if quant.is_fabric and quant.fabric_pieces and quant.quantity:
                quant.fabric_avg_weight = quant.quantity / quant.fabric_pieces
            else:
                quant.fabric_avg_weight = 0.0


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Total fabric weight on hand (computed from quants)
    fabric_weight_on_hand = fields.Float(
        string='الوزن في المخزون (كجم)',
        compute='_compute_fabric_on_hand',
        digits=(16, 3),
    )

    # Total fabric pieces on hand
    fabric_pieces_on_hand = fields.Float(
        string='عدد الأتواب في المخزون',
        compute='_compute_fabric_on_hand',
        digits=(16, 2),
    )

    # Total fabric meters on hand
    fabric_meters_on_hand = fields.Float(
        string='إجمالي الأمتار في المخزون',
        compute='_compute_fabric_on_hand',
        digits=(16, 2),
    )

    def _compute_fabric_on_hand(self):
        for product in self:
            if product.is_fabric:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal'),
                ])
                product.fabric_weight_on_hand = sum(quants.mapped('quantity'))
                product.fabric_pieces_on_hand = sum(quants.mapped('fabric_pieces'))
                product.fabric_meters_on_hand = sum(quants.mapped('fabric_meters'))
            else:
                product.fabric_weight_on_hand = 0.0
                product.fabric_pieces_on_hand = 0.0
                product.fabric_meters_on_hand = 0.0

    def action_view_fabric_stock(self):
        """Open quants view showing fabric weight details"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_view_quants')
        action['domain'] = [('product_id', '=', self.id), ('location_id.usage', '=', 'internal')]
        action['context'] = {'search_default_internal_loc': 1}
        return action

