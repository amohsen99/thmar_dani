# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_type = fields.Selection(
        selection=[
            ('cash', 'كاش'),
            ('credit', 'اجل'),
        ],
        string='نوع الفاتورة',
        default='cash',
    )
    permission_number = fields.Char(
        string='رقم الاذن',
    )
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='المخزن',
    )
