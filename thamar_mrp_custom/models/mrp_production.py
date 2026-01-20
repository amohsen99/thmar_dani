# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'



    # Features Tab Fields

    finishing_type = fields.Selection([
        ('womens', 'Womens'),
        ('mens', 'Mens'),
        ('kids', 'Kids'),
        ('custom', 'custom'),
    ], string='Finishing Type', tracking=True, help='Type of finishing for this manufacturing order')

    fabric_type_id = fields.Many2one(
        'mrp.fabric.type',
        string='Fabric Type',
        tracking=True,
        help='Construction or material name of the fabric'
    )

    operation = fields.Selection([
        ('printing', 'Printing'),
        ('dyeing', 'Dyeing'),
        ('printing_dyeing', 'Printing & Dyeing')
    ], string='Operation', tracking=True, help='Processing stage for this manufacturing order')

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

    product_weight = fields.Float(
        string='Product Weight',
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

    @api.depends('width', 'product_weight')
    def _compute_average(self):
        for record in self:
            if record.width and record.product_weight and record.width != 0:
                # Formula: (1000/(width/product_weight))*100
                record.average = (1000 / (record.width / record.product_weight)) * 100
            else:
                record.average = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to sync features from product
        """
        productions = super().create(vals_list)

        for production in productions:
            # Sync from product if it has features
            if production.product_id and production.product_id.has_features:
                production._sync_features_from_product()

        return productions

    def _sync_features_from_product(self):
        """
        Sync features from product to this manufacturing order
        """
        self.ensure_one()

        if self.product_id and self.product_id.has_features:
            self.write({
                'finishing_type': self.product_id.finishing_type,
                'fabric_type_id': self.product_id.fabric_type_id.id,
                'operation': self.product_id.operation,
                'packing_type': self.product_id.packing_type,
                'stripe': self.product_id.stripe,
                'color_id': self.product_id.color_id.id,
                'width': self.product_id.width,
                'product_weight': self.product_id.product_weight,
                'design_id': self.product_id.design_id.id,
            })
    #
