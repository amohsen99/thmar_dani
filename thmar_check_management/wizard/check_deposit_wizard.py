# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CheckDepositWizard(models.TransientModel):
    """Wizard to deposit one or more checks into a bank for collection."""
    _name = 'check.deposit.wizard'
    _description = 'Check Deposit Wizard / إيداع الشيكات بالبنك'

    deposit_date = fields.Date(
        string='Deposit Date / تاريخ الإيداع',
        required=True,
        default=fields.Date.context_today
    )
    bank_journal_id = fields.Many2one(
        'account.journal',
        string='Collecting Bank Journal / بنك التحصيل',
        domain="[('type', '=', 'bank')]",
        required=True
    )
    check_ids = fields.Many2many(
        'account.check',
        string='Checks / الشيكات',
        required=True
    )
    total_amount = fields.Monetary(
        string='Total Amount / إجمالي الشيكات',
        compute='_compute_total_amount',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    notes = fields.Text(string='Notes / ملاحظات')

    @api.depends('check_ids.amount')
    def _compute_total_amount(self):
        for wiz in self:
            wiz.total_amount = sum(wiz.check_ids.mapped('amount'))

    def action_confirm_deposit(self):
        self.ensure_one()
        if not self.check_ids:
            raise UserError(_("No checks selected for deposit."))

        company = self.env.company
        under_collection_acc = company.check_under_collection_account_id
        if not under_collection_acc:
            raise UserError(_("Please configure the Under Collection Account (حساب شيكات برسم التحصيل) in Cheque Settings."))

        notes_receivable_acc = company.check_receivable_account_id
        if not notes_receivable_acc:
            raise UserError(_("Please configure the Notes Receivable Account (حساب أوراق القبض) in Cheque Settings."))

        journal = company.check_journal_id or self.bank_journal_id

        # Generate single journal entry for batch deposit
        financial_checks = self.check_ids.filtered(lambda c: not c.is_guarantee)
        tot_amount = sum(financial_checks.mapped('amount'))

        move = False
        if tot_amount > 0:
            check_names = ", ".join(self.check_ids.mapped('name'))
            line_vals = [
                {
                    'name': _("إيداع شيكات برسم التحصيل (%s) لدى بنك %s") % (check_names, self.bank_journal_id.name),
                    'account_id': under_collection_acc.id,
                    'debit': tot_amount,
                    'credit': 0.0,
                },
                {
                    'name': _("خروج شيكات من الخزينة برسم التحصيل (%s)") % check_names,
                    'account_id': notes_receivable_acc.id,
                    'debit': 0.0,
                    'credit': tot_amount,
                }
            ]
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': self.deposit_date,
                'journal_id': journal.id,
                'ref': _("حافظة إيداع بنكي - %s") % self.bank_journal_id.name,
                'line_ids': [(0, 0, lv) for lv in line_vals],
            })
            move.action_post()

        # Update checks
        for check in self.check_ids:
            vals = {
                'state': 'deposited',
                'deposit_date': self.deposit_date,
                'deposit_bank_journal_id': self.bank_journal_id.id,
            }
            if move:
                vals['move_ids'] = [(4, move.id)]
            check.write(vals)

        return {'type': 'ir.actions.act_window_close'}
