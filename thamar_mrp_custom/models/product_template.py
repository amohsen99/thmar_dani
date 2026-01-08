# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Checkbox to enable features
    has_features = fields.Boolean(
        string='Has Product Features',
        default=False,
        help='Enable this to add product specifications (finishing type, color, design, etc.)'
    )

    # Features Tab Fields
    finishing_type = fields.Selection([
        ('womens', 'Womens'),
        ('mens', 'Mens'),
        ('kids', 'Kids'),
        ('custom', 'custom'),
    ], string='Finishing Type', help='Type of finishing for this product')

    packing_type = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')
    ], string='Packing Type', help='Type of packing for this product')

    stripe = fields.Selection([
        ('white', 'White'),
        ('alomar', 'Al-Omar'),
        ('althamar', 'Al-Thamar'),
        ('client', 'Client')
    ], string='Stripe', help='Stripe type for this product')

    color_id = fields.Many2one(
        'mrp.color',
        string='Color',
        help='Color for this product'
    )

    width = fields.Float(
        string='Width',
        digits=(16, 2),
        help='Width of the product'
    )

    weight = fields.Float(
        string='Weight',
        digits=(16, 2),
        help='Weight of the product'
    )

    density = fields.Float(
        string='Density',
        digits=(16, 2),
        help='Density of the product'
    )

    design_id = fields.Many2one(
        'mrp.design',
        string='Design',
        help='Design for this product'
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

    @api.onchange('has_features')
    def _onchange_has_features(self):
        """
        Clear feature fields when has_features is unchecked
        """
        if not self.has_features:
            self.finishing_type = False
            self.packing_type = False
            self.stripe = False
            self.color_id = False
            self.width = 0.0
            self.weight = 0.0
            self.density = 0.0
            self.design_id = False

