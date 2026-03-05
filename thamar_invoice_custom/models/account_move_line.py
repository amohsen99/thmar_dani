# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    bank_id = fields.Many2one(
        'res.bank',
        string='Bank',
        compute='_compute_cheque_fields',
        store=True,
        readonly=False,
        help='Bank for cheque payment'
    )
    cheque_due_date = fields.Date(
        string='Cheque Due Date',
        compute='_compute_cheque_fields',
        store=True,
        readonly=False,
        help='Due date for cheque payment'
    )
    cheque_number = fields.Char(
        string='Cheque Number',
        compute='_compute_cheque_fields',
        store=True,
        readonly=False,
        help='Cheque number for payment'
    )

    @api.depends('payment_id', 'payment_id.cheque_number', 'payment_id.bank_id', 'payment_id.cheque_due_date')
    def _compute_cheque_fields(self):
        for line in self:
            if line.payment_id:
                if line.payment_id.cheque_number:
                    line.cheque_number = line.payment_id.cheque_number
                if line.payment_id.bank_id:
                    line.bank_id = line.payment_id.bank_id
                if line.payment_id.cheque_due_date:
                    line.cheque_due_date = line.payment_id.cheque_due_date
            # Else preserve manually entered bank_id/cheque_number/etc
