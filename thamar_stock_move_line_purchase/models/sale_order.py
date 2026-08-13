# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    authorization_number = fields.Char(
        string='رقم الاذن',
        copy=True,
        tracking=True,
    )
