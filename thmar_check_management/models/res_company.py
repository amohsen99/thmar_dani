# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    check_journal_id = fields.Many2one(
        'account.journal',
        string='Cheque Journal / دفتر يومية الشيكات',
        domain="[('type', 'in', ('general', 'bank', 'cash'))]",
        help='Default journal used for cheque transactions and clearing entries.'
    )
    check_receivable_account_id = fields.Many2one(
        'account.account',
        string='Notes Receivable Account / حساب أوراق القبض (بالخزينة)',
        help='Account holding incoming checks currently in the safe/drawer.'
    )
    check_under_collection_account_id = fields.Many2one(
        'account.account',
        string='Under Collection Account / حساب شيكات برسم التحصيل',
        help='Account holding checks deposited in bank under collection.'
    )
    check_endorsed_account_id = fields.Many2one(
        'account.account',
        string='Endorsed Cheques Clearing Account / حساب تسوية الشيكات المظهرة',
        help='Intermediate account for endorsed cheques transferred to third parties.'
    )
    check_bounced_account_id = fields.Many2one(
        'account.account',
        string='Bounced Cheques Account / حساب الشيكات المرتدة',
        help='Account holding returned/bounced cheques.'
    )
    check_payable_account_id = fields.Many2one(
        'account.account',
        string='Notes Payable Account / حساب أوراق الدفع (شيكات صادرة)',
        help='Account for outgoing checks issued by the company to vendors.'
    )
    check_discount_expense_account_id = fields.Many2one(
        'account.account',
        string='Discounting Expense Account / حساب فوائد ومصاريف الخصم',
        help='Expense account for cheque discounting interest and bank commission.'
    )
