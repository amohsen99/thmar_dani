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

    finishing_type=fields.Selection([
        ('printing', 'Printing'),
        ('drying', 'Drying'),
    ], string='Finishing Type', help='Type of finishing for this manufacturing order')
    color_id = fields.Many2one(
        'mrp.color',
        string='Color',
        help='Color for this manufacturing order'
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

