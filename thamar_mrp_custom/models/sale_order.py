# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    operation = fields.Selection([
        ('printing', 'Printing'),
        ('dyeing', 'Dyeing'),
        ('printing_dyeing', 'Printing & Dyeing')
    ], string='Operation', help='Processing stage')
