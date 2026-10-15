# -*- coding: utf-8 -*-
from odoo import models, fields


class CartellaFinishedProduct(models.Model):
    """المنتج التام - Finished Product master data"""
    _name = 'cartella.finished.product'
    _description = 'المنتج التام'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(
        string='اسم المنتج التام',
        required=True,
    )
    code = fields.Char(
        string='كود المنتج التام',
        required=True,
    )

    _code_unique = models.Constraint(
        'unique(code)',
        'كود المنتج التام يجب أن يكون فريداً!',
    )
