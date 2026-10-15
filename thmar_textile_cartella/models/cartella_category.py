# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CartellaCategory(models.Model):
    """فئة الكارتيلة - Category"""
    _name = 'cartella.category'
    _description = 'فئة الكارتيلة'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(
        string='اسم الفئة',
        required=True,
    )
    code = fields.Char(
        string='كود الفئة',
        required=True,
    )

    _code_unique = models.Constraint(
        'unique(code)',
        'كود الفئة يجب أن يكون فريداً!',
    )
