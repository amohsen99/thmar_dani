# -*- coding: utf-8 -*-
from odoo import models, fields


class MrpFabricType(models.Model):
    _name = 'mrp.fabric.type'
    _description = 'Fabric Type'
    _order = 'name'

    name = fields.Char(
        string='Fabric Type',
        required=True,
        help='Construction or material name of the fabric'
    )

    active = fields.Boolean(
        default=True,
        help='If unchecked, it will allow you to hide the fabric type without removing it.'
    )

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Fabric type name must be unique!'),
    ]
