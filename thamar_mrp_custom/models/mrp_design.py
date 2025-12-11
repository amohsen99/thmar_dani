# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpDesign(models.Model):
    _name = 'mrp.design'
    _description = 'Manufacturing Design'
    _order = 'name'

    name = fields.Char(
        string='Design Name',
        required=True,
        help='Name of the design'
    )
    
    image = fields.Image(
        string='Design Image',
        help='Image of the design'
    )
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Design name must be unique!'),
    ]

