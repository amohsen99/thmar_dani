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
                lambda c: c.state == 'in_safe' and c.check_type == 'incoming'
            )
            if not valid_checks:
                raise UserError(_("Please select incoming checks in safe to deposit. / يرجى اختيار شيكات واردة وبحالة في الخزينة للإيداع."))
            res['check_ids'] = [(6, 0, valid_checks.ids)]
        return res

    @api.depends('check_ids.amount')
    def _compute_total_amount(self):
        for wiz in self:
            wiz.total_amount = sum(wiz.check_ids.mapped('amount'))

    def action_confirm_deposit(self):
        self.ensure_one()
        if not self.check_ids:
            raise UserError(_("No checks selected for deposit."))

        invalid_checks = self.check_ids.filtered(lambda c: c.state != 'in_safe' or c.check_type != 'incoming')
        if invalid_checks:
            names = ", ".join(invalid_checks.mapped('name'))
            raise UserError(_("The following checks cannot be deposited (only incoming checks in safe): %s") % names)

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
                }
            ]
            for check in financial_checks:
                line_vals.append({
                    'name': _("خروج شيك رقم %s من الخزينة برسم التحصيل") % check.name,
                    'account_id': notes_receivable_acc.id,
                    'partner_id': check.partner_id.id,
                    'debit': 0.0,
                    'credit': check.amount,
                })

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
