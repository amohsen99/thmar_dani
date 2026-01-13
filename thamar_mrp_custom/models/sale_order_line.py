# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Check if product has features
    product_has_features = fields.Boolean(
        string='Product Has Features',
        related='product_id.has_features',
        store=True,
        help='True if the product has features enabled'
    )

    # Features Tab Fields
    finishing_type = fields.Selection([
        ('womens', 'Womens'),
        ('mens', 'Mens'),
        ('kids', 'Kids'),
        ('custom', 'custom'),
    ], string='Finishing Type', help='Type of finishing for this line')

    fabric_type_id = fields.Many2one(
        'mrp.fabric.type',
        string='Fabric Type',
        help='Construction or material name of the fabric'
    )

    operation = fields.Selection([
        ('printing', 'Printing'),
        ('dyeing', 'Dyeing'),
        ('printing_dyeing', 'Printing & Dyeing')
    ], string='Operation', help='Processing stage for this line')

    packing_type = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')
    ], string='Packing Type', help='Type of packing for this line')

    stripe = fields.Selection([
        ('white', 'White'),
        ('alomar', 'Al-Omar'),
        ('althamar', 'Al-Thamar'),
        ('client', 'Client')
    ], string='Stripe', help='Stripe type for this line')

    color_id = fields.Many2one(
        'mrp.color',
        string='Color',
        help='Color for this line'
    )

    width = fields.Float(
        string='Width',
        digits=(16, 2),
        help='Width of the product'
    )

    product_weight = fields.Float(
        string='Product Weight',
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
        help='Design for this line'
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

    @api.onchange('product_id')
    def _onchange_product_id_copy_features(self):
        """
        Auto-fill features from product when product is selected
        """
        if self.product_id and self.product_id.has_features:
            self.finishing_type = self.product_id.finishing_type
            self.fabric_type_id = self.product_id.fabric_type_id
            self.operation = self.product_id.operation
            self.packing_type = self.product_id.packing_type
            self.stripe = self.product_id.stripe
            self.color_id = self.product_id.color_id
            self.width = self.product_id.width
            self.product_weight = self.product_id.product_weight
            self.density = self.product_id.density
            self.design_id = self.product_id.design_id

    @api.constrains('product_id', 'finishing_type', 'fabric_type_id', 'packing_type', 'stripe', 'color_id',
                    'design_id', 'width', 'product_weight', 'density')
    def _check_features_required(self):
        """
        Validate that features are filled when product has features enabled
        """
        for line in self:
            if line.product_id and line.product_id.has_features:
                if not line.finishing_type:
                    raise ValidationError(f'Finishing Type is required for product "{line.product_id.name}"')
                if not line.fabric_type_id:
                    raise ValidationError(f'Fabric Type is required for product "{line.product_id.name}"')
                if not line.operation:
                    raise ValidationError(f'Operation is required for product "{line.product_id.name}"')
                if not line.packing_type:
                    raise ValidationError(f'Packing Type is required for product "{line.product_id.name}"')
                if not line.stripe:
                    raise ValidationError(f'Stripe is required for product "{line.product_id.name}"')
                if not line.color_id:
                    raise ValidationError(f'Color is required for product "{line.product_id.name}"')
                if not line.design_id:
                    raise ValidationError(f'Design is required for product "{line.product_id.name}"')
                if not line.width:
                    raise ValidationError(f'Width is required for product "{line.product_id.name}"')
                if not line.product_weight:
                    raise ValidationError(f'Weight is required for product "{line.product_id.name}"')
                if not line.density:
                    raise ValidationError(f'Density is required for product "{line.product_id.name}"')

