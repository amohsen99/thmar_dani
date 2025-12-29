# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Check if any product in order lines has features
    has_featured_products = fields.Boolean(
        string='Has Featured Products',
        compute='_compute_has_featured_products',
        store=True,
        help='True if any product in order lines has features enabled'
    )

    # Manufacturing Order relation
    mrp_production_ids = fields.One2many(
        'mrp.production',
        'sale_order_id',
        string='Manufacturing Orders',
        help='Manufacturing orders related to this sale order'
    )


    mrp_production_count = fields.Integer(
        string='MO Count',
        compute='_compute_mrp_production_count',
        help='Number of manufacturing orders'
    )

    @api.depends('order_line', 'order_line.product_id', 'order_line.product_id.has_features')
    def _compute_has_featured_products(self):
        for record in self:
            record.has_featured_products = any(
                line.product_id.has_features for line in record.order_line
            )

    @api.depends('mrp_production_ids')
    def _compute_mrp_production_count(self):
        for record in self:
            record.mrp_production_count = len(record.mrp_production_ids)

    def action_view_mrp_production(self):
        """
        Smart button action to view related manufacturing orders
        """
        self.ensure_one()
        action = self.env.ref('mrp.mrp_production_action').read()[0]
        
        if len(self.mrp_production_ids) > 1:
            action['domain'] = [('id', 'in', self.mrp_production_ids.ids)]
        elif len(self.mrp_production_ids) == 1:
            action['views'] = [(self.env.ref('mrp.mrp_production_form_view').id, 'form')]
            action['res_id'] = self.mrp_production_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        
        return action

    def _action_confirm(self):
        """
        Override to copy features from order lines to manufacturing orders when SO is confirmed
        """
        res = super(SaleOrder, self)._action_confirm()

        # Copy features from order lines to related manufacturing orders
        for order in self:
            if order.mrp_production_ids:
                order._sync_features_to_mrp_from_lines()

        return res

    def _sync_features_to_mrp_from_lines(self):
        """
        Sync features from sale order lines to manufacturing orders
        Each MO gets features from its corresponding sale order line
        """
        self.ensure_one()

        for mo in self.mrp_production_ids:
            # Find the sale order line for this product
            # Simple approach: match by product_id
            sale_line = self.order_line.filtered(
                lambda l: l.product_id == mo.product_id and l.product_id.has_features
            )[:1]

            if sale_line and sale_line.product_has_features:
                mo.write({
                    'finishing_type': sale_line.finishing_type,
                    'packing_type': sale_line.packing_type,
                    'stripe': sale_line.stripe,
                    'color_id': sale_line.color_id.id,
                    'width': sale_line.width,
                    'weight': sale_line.weight,
                    'density': sale_line.density,
                    'design_id': sale_line.design_id.id,
                })

