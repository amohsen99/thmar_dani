# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    authorization_number = fields.Char(
        string='رقم الاذن',
        copy=True,
        tracking=True,
    )
