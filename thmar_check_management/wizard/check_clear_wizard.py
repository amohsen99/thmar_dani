# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CheckClearWizard(models.TransientModel):
    """Wizard to record clearance/collection of checks into the bank."""
    _name = 'check.clear.wizard'
    _description = 'Check Clear Wizard / إثبات تحصيل أو صرف الشيك'

    clear_date = fields.Date(
        string='Clearance Date / تاريخ الصرف أو الإيداع الفعلي',
        required=True,
        default=fields.Date.context_today
    )
    bank_journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal / حساب البنك المحصل فيه',
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
    fee_amount = fields.Monetary(
        string='Bank Collection Fee / عمولة أو مصاريف بنكية',
        default=0.0,
        currency_field='currency_id'
    )
    fee_account_id = fields.Many2one(
        'account.account',
        string='Bank Fees Account / حساب مصاريف التحصيل البنكية'
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

    @api.onchange('check_ids')
    def _onchange_check_ids(self):
        if self.check_ids and not self.bank_journal_id:
            # If deposited, prefill deposit bank
            dep_bank = self.check_ids[0].deposit_bank_journal_id
            if dep_bank:
                self.bank_journal_id = dep_bank

    def action_confirm_clear(self):
        self.ensure_one()
        if not self.check_ids:
            raise UserError(_("No checks selected."))

        company = self.env.company
        bank_acc = self.bank_journal_id.default_account_id
        if not bank_acc:
            raise UserError(_("The selected bank journal '%s' has no default debit account.") % self.bank_journal_id.name)

        if self.fee_amount > 0 and not self.fee_account_id:
            raise UserError(_("Please select a Bank Fees Account when entering a fee amount."))

        financial_checks = self.check_ids.filtered(lambda c: not c.is_guarantee)
        tot_amount = sum(financial_checks.mapped('amount'))

        move = False
        if tot_amount > 0:
            net_bank_amount = tot_amount - self.fee_amount
            check_names = ", ".join(self.check_ids.mapped('name'))
            line_vals = []

            # Check if these are incoming or outgoing
            is_incoming = all(c.check_type == 'incoming' for c in self.check_ids)

            if is_incoming:
                # Debit: Bank (Net Amount)
                line_vals.append({
                    'name': _("تحصيل شيكات رقم (%s) بالبنك") % check_names,
                    'account_id': bank_acc.id,
                    'debit': net_bank_amount,
                    'credit': 0.0,
                })
                # Debit: Fees (if any)
                if self.fee_amount > 0:
                    line_vals.append({
                        'name': _("عمولة ومصاريف تحصيل شيكات (%s)") % check_names,
                        'account_id': self.fee_account_id.id,
                        'debit': self.fee_amount,
                        'credit': 0.0,
                    })

                # Credit: Under Collection or Notes Receivable
                for check in financial_checks:
                    credit_acc = (
                        company.check_under_collection_account_id
                        if check.state == 'deposited'
                        else company.check_receivable_account_id
                    )
                    if not credit_acc:
                        raise UserError(_("Please configure the Cheque Accounts in Settings."))
                    line_vals.append({
                        'name': _("إقفال شيك رقم %s بعد التحصيل") % check.name,
                        'account_id': credit_acc.id,
                        'partner_id': check.partner_id.id,
                        'debit': 0.0,
                        'credit': check.amount,
                    })
            else:
                # Outgoing checks being cleared/debited from bank:
                payable_acc = company.check_payable_account_id
                if not payable_acc:
                    raise UserError(_("Please configure the Notes Payable Account in Cheque Settings."))
                line_vals.append({
                    'name': _("صرف شيكات أوراق دفع رقم (%s)") % check_names,
                    'account_id': payable_acc.id,
                    'debit': tot_amount,
                    'credit': 0.0,
                })
                line_vals.append({
                    'name': _("خصم من البنك لصرف شيكات (%s)") % check_names,
                    'account_id': bank_acc.id,
                    'debit': 0.0,
                    'credit': tot_amount,
                })

            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': self.clear_date,
                'journal_id': self.bank_journal_id.id,
                'ref': _("إشعار تحصيل/صرف شيكات - %s") % self.bank_journal_id.name,
                'line_ids': [(0, 0, lv) for lv in line_vals],
            })
            move.action_post()

        # Update checks
        for check in self.check_ids:
            vals = {
                'state': 'cleared',
                'clear_date': self.clear_date,
            }
            if move:
                vals['move_ids'] = [(4, move.id)]
            check.write(vals)

        return {'type': 'ir.actions.act_window_close'}
