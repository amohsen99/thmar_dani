# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


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

    def _post(self, soft=True):
        for move in self.filtered(lambda m: not m.name or m.name == '/'):
            if move.move_type == 'out_invoice':
                move.name = self.env['ir.sequence'].next_by_code('account.move.invoice') or '/'
            elif move.move_type == 'in_invoice':
                move.name = self.env['ir.sequence'].next_by_code('account.move.bill') or '/'
        return super()._post(soft=soft)
