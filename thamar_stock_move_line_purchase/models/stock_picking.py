# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    authorization_number = fields.Char(
        string='رقم الاذن',
        compute='_compute_authorization_number',
        store=True,
        # readonly=False,
    )

    @api.depends('sale_id.authorization_number', 'purchase_id.authorization_number')
    def _compute_authorization_number(self):
        for picking in self:
            if picking.sale_id and picking.sale_id.authorization_number:
                picking.authorization_number = picking.sale_id.authorization_number
            elif picking.purchase_id and picking.purchase_id.authorization_number:
                picking.authorization_number = picking.purchase_id.authorization_number
            elif not picking.authorization_number:
                picking.authorization_number = False
