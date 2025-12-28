# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Features Tab Fields (same as MRP Production)
    finishing_type = fields.Selection([
        ('womens', 'Womens'),
        ('mens', 'Mens'),
        ('kids', 'Kids'),
        ('custom', 'custom'),
    ], string='Finishing Type', required=True, tracking=True, help='Type of finishing for this order')

    packing_type = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')
    ], string='Packing Type', required=True, tracking=True, help='Type of packing for this order')

    stripe = fields.Selection([
        ('white', 'White'),
        ('alomar', 'Al-Omar'),
        ('althamar', 'Al-Thamar'),
        ('client', 'Client')
    ], string='Stripe', required=True, tracking=True, help='Stripe type for this order')

    color_id = fields.Many2one(
        'mrp.color',
        string='Color',
        required=True,
        tracking=True,
        help='Color for this order'
    )

    width = fields.Float(
        string='Width',
        digits=(16, 2),
        required=True,
        tracking=True,
        help='Width of the product'
    )

    weight = fields.Float(
        string='Weight',
        digits=(16, 2),
        required=True,
        tracking=True,
        help='Weight of the product'
    )

    density = fields.Float(
        string='Density',
        digits=(16, 2),
        required=True,
        tracking=True,
        help='Density of the product'
    )

    design_id = fields.Many2one(
        'mrp.design',
        string='Design',
        required=True,
        tracking=True,
        help='Design for this order'
    )

    design_image = fields.Image(
        string='Design Image',
        related='design_id.image',
        readonly=True,
        help='Image from the selected design'
    )

    average = fields.Float(
        string='Average',
        compute='_compute_average',
        store=True,
        digits=(16, 2),
        help='Computed as: (1000/(width/weight))*100'
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

    @api.depends('width', 'weight')
    def _compute_average(self):
        for record in self:
            if record.width and record.weight and record.width != 0:
                # Formula: (1000/(width/weight))*100
                record.average = (1000 / (record.width / record.weight)) * 100
            else:
                record.average = 0.0

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
        Override to copy features to manufacturing orders when SO is confirmed
        """
        res = super(SaleOrder, self)._action_confirm()
        
        # Copy features to related manufacturing orders
        for order in self:
            if order.mrp_production_ids:
                order._sync_features_to_mrp()
        
        return res

    def _sync_features_to_mrp(self):
        """
        Sync features from sale order to manufacturing orders
        """
        self.ensure_one()

        feature_values = {
            'finishing_type': self.finishing_type,
            'packing_type': self.packing_type,
            'stripe': self.stripe,
            'color_id': self.color_id.id,
            'width': self.width,
            'weight': self.weight,
            'density': self.density,
            'design_id': self.design_id.id,
        }

        # Update all related manufacturing orders
        self.mrp_production_ids.write(feature_values)

