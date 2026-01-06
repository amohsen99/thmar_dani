# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Enable fabric tracking
    is_fabric = fields.Boolean(
        string='قماش / Is Fabric',
        default=False,
        tracking=True,
        help='Enable fabric weight tracking - weight is primary, pieces are secondary'
    )

    # Approximate weight per piece (توب)
    fabric_approx_weight = fields.Float(
        string='الوزن التقريبي للتوب (كجم)',
        digits=(16, 3),
        default=25.0,
        tracking=True,
        help='Approximate weight per piece (توب) in Kg. Used to auto-calculate number of pieces.'
    )
    # Approximate meters per piece (توب)
    fabric_approx_meters = fields.Float(
        string='الأمتار التقريبية للتوب',
        digits=(16, 2),
        default=30.0,
        tracking=True,
        help='Approximate meters per piece (توب). Used to auto-calculate total meters.'
    )
