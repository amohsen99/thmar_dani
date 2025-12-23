# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpColorCategory(models.Model):
    _name = 'mrp.color.category'
    _description = 'Color Category'
    _order = 'name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help='Name of the color category'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the category'
    )
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Category name must be unique!'),
    ]

