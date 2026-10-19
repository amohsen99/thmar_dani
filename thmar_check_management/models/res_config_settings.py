# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    check_journal_id = fields.Many2one(
        related='company_id.check_journal_id',
        string='Cheque Journal / دفتر يومية الشيكات',
        readonly=False,
    )
    check_receivable_account_id = fields.Many2one(
        related='company_id.check_receivable_account_id',
        string='Notes Receivable Account / حساب أوراق القبض (بالخزينة)',
        readonly=False,
    )
    check_under_collection_account_id = fields.Many2one(
        related='company_id.check_under_collection_account_id',
        string='Under Collection Account / حساب شيكات برسم التحصيل',
        readonly=False,
    )
    check_endorsed_account_id = fields.Many2one(
        related='company_id.check_endorsed_account_id',
        string='Endorsed Cheques Clearing Account / حساب تسوية الشيكات المظهرة',
        readonly=False,
    )
    check_bounced_account_id = fields.Many2one(
        related='company_id.check_bounced_account_id',
        string='Bounced Cheques Account / حساب الشيكات المرتدة',
        readonly=False,
    )
    check_payable_account_id = fields.Many2one(
        related='company_id.check_payable_account_id',
        string='Notes Payable Account / حساب أوراق الدفع (شيكات صادرة)',
        readonly=False,
    )
    check_discount_expense_account_id = fields.Many2one(
        related='company_id.check_discount_expense_account_id',
        string='Discounting Expense Account / حساب فوائد ومصاريف الخصم',
        readonly=False,
    )
