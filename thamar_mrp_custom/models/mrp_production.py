# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        help='Customer for this manufacturing order'
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        help='Related sale order for this manufacturing order'
    )

    # Features Tab Fields

    finishing_type = fields.Selection([
        ('womens', 'Womens'),
        ('mens', 'Mens'),
        ('kids', 'Kids'),
        ('custom', 'custom'),
    ], string='Finishing Type', tracking=True, help='Type of finishing for this manufacturing order')

    packing_type = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')
    ], string='Packing Type', tracking=True, help='Type of packing for this manufacturing order')

    stripe = fields.Selection([
        ('white', 'White'),
        ('alomar', 'Al-Omar'),
        ('althamar', 'Al-Thamar'),
        ('client', 'Client')
    ], string='Stripe', tracking=True, help='Stripe type for this manufacturing order')

    color_id = fields.Many2one(
        'mrp.color',
        string='Color',
        tracking=True,
        help='Color for this manufacturing order'
    )

    width = fields.Float(
        string='Width',
        digits=(16, 2),
        tracking=True,
        help='Width of the product'
    )

    weight = fields.Float(
        string='Weight',
        digits=(16, 2),
        tracking=True,
        help='Weight of the product'
    )

    density = fields.Float(
        string='Density',
        digits=(16, 2),
        tracking=True,
        help='Density of the product'
    )

    design_id = fields.Many2one(
        'mrp.design',
        string='Design',
        tracking=True,
        help='Design for this manufacturing order'
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

    @api.depends('width', 'weight')
    def _compute_average(self):
        for record in self:
            if record.width and record.weight and record.width != 0:
                # Formula: (1000/(width/weight))*100
                record.average = (1000 / (record.width / record.weight)) * 100
            else:
                record.average = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to sync features from sale order or product
        """
        productions = super(MrpProduction, self).create(vals_list)

        for production in productions:
            # Priority 1: Sync from sale order if available
            if production.sale_order_id:
                production._sync_features_from_sale_order()
            # Priority 2: Sync from product if it has features
            elif production.product_id and production.product_id.has_features:
                production._sync_features_from_product()

        return productions

    @api.onchange('product_id')
    def _onchange_product_id_copy_features(self):
        """
        Auto-fill features from product when product is selected
        """
        if self.product_id and self.product_id.has_features:
            self.finishing_type = self.product_id.finishing_type
            self.packing_type = self.product_id.packing_type
            self.stripe = self.product_id.stripe
            self.color_id = self.product_id.color_id
            self.width = self.product_id.width
            self.weight = self.product_id.weight
            self.density = self.product_id.density
            self.design_id = self.product_id.design_id

    def _sync_features_from_sale_order(self):
        """
        Sync features from related sale order LINE to this manufacturing order
        """
        self.ensure_one()

        if self.sale_order_id:
            # Find the sale order line for this product
            sale_line = self.sale_order_id.order_line.filtered(
                lambda l: l.product_id == self.product_id and l.product_id.has_features
            )[:1]

            if sale_line and sale_line.product_has_features:
                self.write({
                    'finishing_type': sale_line.finishing_type,
                    'packing_type': sale_line.packing_type,
                    'stripe': sale_line.stripe,
                    'color_id': sale_line.color_id.id,
                    'width': sale_line.width,
                    'weight': sale_line.weight,
                    'density': sale_line.density,
                    'design_id': sale_line.design_id.id,
                })

    def _sync_features_from_product(self):
        """
        Sync features from product to this manufacturing order
        """
        self.ensure_one()

        if self.product_id and self.product_id.has_features:
            self.write({
                'finishing_type': self.product_id.finishing_type,
                'packing_type': self.product_id.packing_type,
                'stripe': self.product_id.stripe,
                'color_id': self.product_id.color_id.id,
                'width': self.product_id.width,
                'weight': self.product_id.weight,
                'density': self.product_id.density,
                'design_id': self.product_id.design_id.id,
            })

