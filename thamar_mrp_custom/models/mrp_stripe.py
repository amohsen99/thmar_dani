# -*- coding: utf-8 -*-
from odoo import models, fields

class MrpStripe(models.Model):
    _name = 'mrp.stripe'
    _description = 'MRP Stripe'
    _order = 'name'

    name = fields.Char(string='Stripe', required=True)
