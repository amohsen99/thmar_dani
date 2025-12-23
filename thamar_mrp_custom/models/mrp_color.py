# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpColor(models.Model):
    _name = 'mrp.color'
    _description = 'Manufacturing Color'
    _order = 'name'

    name = fields.Char(
        string='Color Name',
        required=True,
        help='Name of the color'
    )
    
    code = fields.Char(
        string='Color Code',
        help='Code for the color (e.g., hex code or reference code)'
    )

    category_id = fields.Many2one(
        'mrp.color.category',
        string='Category',
        help='Category of the color'
    )

    customer = fields.Char(
        string='Customer',
        help='Customer associated with this color'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the color'
    )
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Color name must be unique!'),
    ]

