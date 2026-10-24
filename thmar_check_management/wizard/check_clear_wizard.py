# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CheckClearWizard(models.TransientModel):
    """Wizard to record clearance/collection of checks into the bank or cash safe."""
    _name = 'check.clear.wizard'
    _description = 'Check Clear Wizard / إثبات تحصيل أو صرف الشيك (بنك أو خزينة)'

    clear_date = fields.Date(
        string='Clearance Date / تاريخ الصرف أو التحصيل الفعلي',
        required=True,
        default=fields.Date.context_today
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Clearing Journal (Bank / Cash) / دفتر اليومية (البنك أو الخزينة)',
        domain="[('type', 'in', ('bank', 'cash'))]",
        required=True
    )
    journal_type = fields.Selection(
        related='journal_id.type',
        string='Journal Type',
        readonly=True
    )
    # Kept for backward compatibility
    bank_journal_id = fields.Many2one(
        'account.journal',
        string='Bank / Cash Journal',
        compute='_compute_bank_journal_id',
        inverse='_inverse_bank_journal_id',
        store=True,
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

    @api.depends('journal_id')
    def _compute_bank_journal_id(self):
        for wiz in self:
            wiz.bank_journal_id = wiz.journal_id

    def _inverse_bank_journal_id(self):
        for wiz in self:
            wiz.journal_id = wiz.bank_journal_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        check_ids = []
        if res.get('check_ids'):
            raw = res['check_ids']
            if isinstance(raw, list) and len(raw) and isinstance(raw[0], (list, tuple)) and len(raw[0]) == 3 and raw[0][0] == 6:
                check_ids = raw[0][2]
            elif isinstance(raw, (list, tuple)):
                check_ids = [i for i in raw if isinstance(i, int)]
        elif self.env.context.get('active_model') == 'account.check' and self.env.context.get('active_ids'):
            check_ids = self.env.context.get('active_ids')

        if check_ids and 'check_ids' in fields_list:
            valid_checks = self.env['account.check'].browse(check_ids).filtered(
                lambda c: c.state in ('deposited', 'in_safe', 'endorsed')
            )
            if not valid_checks:
                raise UserError(_("Selected check(s) cannot be cleared in their current status. / لا يمكن تحصيل أو صرف الشيكات المختارة في حالتها الحالية."))
            res['check_ids'] = [(6, 0, valid_checks.ids)]
            if not res.get('journal_id') and not res.get('bank_journal_id'):
                dep_bank = valid_checks[0].deposit_bank_journal_id
                if dep_bank:
                    res['journal_id'] = dep_bank.id
                    res['bank_journal_id'] = dep_bank.id
        return res

    @api.depends('check_ids.amount')
    def _compute_total_amount(self):
        for wiz in self:
            wiz.total_amount = sum(wiz.check_ids.mapped('amount'))

    @api.onchange('check_ids')
    def _onchange_check_ids(self):
        if self.check_ids and not self.journal_id:
            dep_bank = self.check_ids[0].deposit_bank_journal_id
            if dep_bank:
                self.journal_id = dep_bank
                self.bank_journal_id = dep_bank

    def action_confirm_clear(self):
        self.ensure_one()
        if not self.check_ids:
            raise UserError(_("No checks selected."))

        invalid_checks = self.check_ids.filtered(lambda c: c.state not in ('deposited', 'in_safe', 'endorsed'))
        if invalid_checks:
            names = ", ".join(invalid_checks.mapped('name'))
            raise UserError(_("The following checks cannot be cleared in their current status: %s") % names)

        # Ensure checks are either all incoming or all outgoing
        types = set(self.check_ids.mapped('check_type'))
        if len(types) > 1:
            raise UserError(_("Please select either all incoming checks or all outgoing checks to clear together. / يرجى اختيار شيكات واردة فقط أو شيكات صادرة فقط للتحصيل معاً."))

        company = self.env.company
        journal = self.journal_id or self.bank_journal_id
        if not journal:
            raise UserError(_("Please select a Bank or Cash journal. / يرجى اختيار حساب البنك أو الخزينة."))

        clear_acc = journal.default_account_id
        if not clear_acc:
            raise UserError(_("The selected journal '%s' has no default account.") % journal.name)

        is_cash = journal.type == 'cash'
        dest_label = _("الخزينة") if is_cash else _("البنك")

        if self.fee_amount > 0 and not self.fee_account_id:
            raise UserError(_("Please select a Bank Fees Account when entering a fee amount."))

        financial_checks = self.check_ids.filtered(lambda c: not c.is_guarantee)
        tot_amount = sum(financial_checks.mapped('amount'))

        move = False
        if tot_amount > 0:
            net_clear_amount = tot_amount - self.fee_amount
            check_names = ", ".join(self.check_ids.mapped('name'))
            line_vals = []

            is_incoming = all(c.check_type == 'incoming' for c in self.check_ids)

            if is_incoming:
                # Debit: Bank or Cash (Net Amount)
                line_vals.append({
                    'name': _("تحصيل شيكات رقم (%s) في %s") % (check_names, dest_label),
                    'account_id': clear_acc.id,
                    'debit': net_clear_amount,
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
                        'name': _("إقفال شيك رقم %s بعد التحصيل في %s") % (check.name, dest_label),
                        'account_id': credit_acc.id,
                        'partner_id': check.partner_id.id,
                        'debit': 0.0,
                        'credit': check.amount,
                    })
            else:
                # Outgoing checks being cleared/debited from bank or cash:
                payable_acc = company.check_payable_account_id
                if not payable_acc:
                    raise UserError(_("Please configure the Notes Payable Account in Cheque Settings."))
                for check in financial_checks:
                    line_vals.append({
                        'name': _("صرف شيك أوراق دفع رقم %s") % check.name,
                        'account_id': payable_acc.id,
                        'partner_id': check.partner_id.id,
                        'debit': check.amount,
                        'credit': 0.0,
                    })
                line_vals.append({
                    'name': _("خصم من %s لصرف شيكات (%s)") % (dest_label, check_names),
                    'account_id': clear_acc.id,
                    'debit': 0.0,
                    'credit': tot_amount,
                })

            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': self.clear_date,
                'journal_id': journal.id,
                'ref': _("إشعار تحصيل/صرف شيكات - %s (%s)") % (journal.name, dest_label),
                'line_ids': [(0, 0, lv) for lv in line_vals],
            })
            move.action_post()

        # Update checks
        for check in self.check_ids:
            vals = {
                'state': 'cleared',
                'clear_date': self.clear_date,
                'clear_journal_id': journal.id,
            }
            if move:
                vals['move_ids'] = [(4, move.id)]
            check.write(vals)

        return {'type': 'ir.actions.act_window_close'}
