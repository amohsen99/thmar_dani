# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Features Tab Fields
    finishing_type = fields.Selection([
        ('womens', 'Womens'),
        ('mens', 'Mens'),
        ('kids', 'Kids'),
        ('custom', 'custom'),
    ], string='Finishing Type', help='Type of finishing for this product')

    custom_finishing = fields.Char(
        string='Custom Finishing',
        help='Describe custom finishing details'
    )

    custom_finishing_image = fields.Image(
        string='Custom Finishing Image'
    )

    fabric_type_id = fields.Many2one(
        'mrp.fabric.type',
        string='Fabric Type',
        help='Construction or material name of the fabric'
    )

    operation = fields.Selection([
        ('printing', 'Printing'),
        ('dyeing', 'Dyeing'),
        ('printing_dyeing', 'Printing & Dyeing')
    ], string='Operation', help='Processing stage for this product')
    

    packing_type = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')
    ], string='Packing Type', help='Type of packing for this product')

    stripe_id = fields.Many2one(
        'mrp.stripe',
        string='Stripe',
        help='Stripe type for this product'
    )

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

    product_weight = fields.Float(
        string='Product Weight',
        digits=(16, 2),
        help='Weight of the product'
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

    @api.depends('width', 'product_weight')
    def _compute_average(self):
        for record in self:
            if record.width and record.product_weight and record.width != 0:
                # Formula: (1000/(width/product_weight))*100
                record.average = (1000 / (record.width / record.product_weight)) * 100
            else:
                record.average = 0.0

    @api.onchange('categ_id', 'fabric_type_id', 'operation', 'color_id', 'design_id')
    def _onchange_features_generate_name(self):
        """
        Generate product name based on features: FabricType-Operation-Color-Design
        Fallbacks to Category if FabricType is missing.
        """
        parts = []
        
        if self.fabric_type_id:
            parts.append(self.fabric_type_id.name)
        elif self.categ_id:
            parts.append(self.categ_id.name)
        
        if self.operation:
            # Get the display label of the selection
            selection_values = self.fields_get(['operation'])['operation']['selection']
            operation_label = dict(selection_values).get(self.operation)
            if operation_label:
                parts.append(operation_label)
        
        if self.color_id:
            parts.append(self.color_id.name)
            
        if self.design_id:
            parts.append(self.design_id.name)
            
        if parts:
            self.name = "-".join(parts)

