# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CheckEndorseWizard(models.TransientModel):
    """Wizard to endorse/transfer checks from the safe to a target partner (Vendor or Customer)."""
    _name = 'check.endorse.wizard'
    _description = 'Check Endorse Wizard / تظهير وتسليم شيكات'

    endorse_date = fields.Date(
        string='Endorsement Date / تاريخ التظهير والتسليم',
        required=True,
        default=fields.Date.context_today
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Beneficiary Partner / الطرف المستلم (المظهر له)',
        required=True,
        help='The customer or vendor receiving this endorsed check to settle their balance.'
    )
    account_id = fields.Many2one(
        'account.account',
        string='Counterpart Account / حساب التسوية',
        compute='_compute_account_id',
        store=True,
        readonly=False
    )
    check_ids = fields.Many2many(
        'account.check',
        string='Checks / الشيكات المراد تظهيرها',
        required=True
    )
    total_amount = fields.Monetary(
        string='Total Amount / إجمالي المبلغ',
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
                raise UserError(_("Only incoming checks in safe can be endorsed. / الشيكات الواردة في الخزينة فقط يمكن تظهيرها لطرف آخر."))
            res['check_ids'] = [(6, 0, valid_checks.ids)]
        return res

    @api.depends('check_ids.amount')
    def _compute_total_amount(self):
        for wiz in self:
            wiz.total_amount = sum(wiz.check_ids.mapped('amount'))

    @api.depends('partner_id')
    def _compute_account_id(self):
        for wiz in self:
            if wiz.partner_id:
                wiz.account_id = (
                    wiz.partner_id.property_account_payable_id
                    or wiz.partner_id.property_account_receivable_id
                )

    def action_confirm_endorse(self):
        self.ensure_one()
        if not self.check_ids:
            raise UserError(_("No checks selected for endorsement."))

        invalid_checks = self.check_ids.filtered(lambda c: c.state != 'in_safe' or c.check_type != 'incoming')
        if invalid_checks:
            names = ", ".join(invalid_checks.mapped('name'))
            raise UserError(_("The following checks cannot be endorsed (must be incoming checks in safe): %s") % names)

        company = self.env.company
        journal = company.check_journal_id or self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', 'in', ('general', 'bank', 'cash'))
        ], limit=1)

        notes_rec_acc = company.check_receivable_account_id
        if not notes_rec_acc:
            raise UserError(_("Please configure the Notes Receivable Account (حساب أوراق القبض) in Cheque Settings."))

        partner_acc = self.account_id or (
            self.partner_id.property_account_payable_id or self.partner_id.property_account_receivable_id
        )
        if not partner_acc:
            raise UserError(_("Please select a Counterpart Account for partner %s.") % self.partner_id.name)

        financial_checks = self.check_ids.filtered(lambda c: not c.is_guarantee)
        tot_amount = sum(financial_checks.mapped('amount'))

        move = False
        if tot_amount > 0 and journal:
            check_names = ", ".join(self.check_ids.mapped('name'))
            line_vals = [
                {
                    'name': _("سداد بتظهير شيكات (%s) إلى %s") % (check_names, self.partner_id.name),
                    'account_id': partner_acc.id,
                    'partner_id': self.partner_id.id,
                    'debit': tot_amount,
                    'credit': 0.0,
                }
            ]
            for check in financial_checks:
                line_vals.append({
                    'name': _("خروج شيك مظهر رقم %s من الخزينة") % check.name,
                    'account_id': notes_rec_acc.id,
                    'partner_id': check.partner_id.id,
                    'debit': 0.0,
                    'credit': check.amount,
                })

            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': self.endorse_date,
                'journal_id': journal.id,
                'ref': _("تظهير شيكات إلى %s") % self.partner_id.name,
                'line_ids': [(0, 0, lv) for lv in line_vals],
            })
            move.action_post()

        # Update checks
        for check in self.check_ids:
            vals = {
                'state': 'endorsed',
                'current_partner_id': self.partner_id.id,
                'endorse_date': self.endorse_date,
            }
            if move:
                vals['move_ids'] = [(4, move.id)]
            check.write(vals)

        return {'type': 'ir.actions.act_window_close'}
