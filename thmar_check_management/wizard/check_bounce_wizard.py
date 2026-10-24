# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CheckBounceWizard(models.TransientModel):
    """Wizard to record bounced/rejected checks and reverse their status."""
    _name = 'check.bounce.wizard'
    _description = 'Check Bounce Wizard / إثبات ارتداد الشيك'

    bounce_date = fields.Date(
        string='Bounce Date / تاريخ الارتداد',
        required=True,
        default=fields.Date.context_today
    )
    bounce_reason = fields.Selection([
        ('insufficient_funds', 'عدم كفاية الرصيد / Insufficient Funds'),
        ('signature_mismatch', 'اختلاف التوقيع / Signature Mismatch'),
        ('account_closed', 'الحساب مغلق / Account Closed'),
        ('technical_error', 'خطأ في التحرير أو التاريخ / Technical/Date Issue'),
        ('stopped_payment', 'إيقاف صرف من الساحب / Payment Stopped'),
        ('other', 'أسباب أخرى / Other')
    ], string='Bounce Reason / سبب الارتداد', required=True, default='insufficient_funds')

    notes = fields.Text(string='Details / تفاصيل الارتداد وملاحظات المتابعة')
    check_ids = fields.Many2many(
        'account.check',
        string='Checks / الشيكات المرتدة',
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
                lambda c: c.state in ('deposited', 'endorsed', 'in_safe')
            )
            if not valid_checks:
                raise UserError(_("Only deposited, endorsed, or in-safe checks can be marked as bounced. / الشيكات المودعة أو المظهرة أو في الخزينة فقط يمكن إثبات ارتدادها."))
            res['check_ids'] = [(6, 0, valid_checks.ids)]
        return res

    @api.depends('check_ids.amount')
    def _compute_total_amount(self):
        for wiz in self:
            wiz.total_amount = sum(wiz.check_ids.mapped('amount'))

    def action_confirm_bounce(self):
        self.ensure_one()
        if not self.check_ids:
            raise UserError(_("No checks selected."))

        invalid_checks = self.check_ids.filtered(lambda c: c.state not in ('deposited', 'endorsed', 'in_safe'))
        if invalid_checks:
            names = ", ".join(invalid_checks.mapped('name'))
            raise UserError(_("The following checks cannot be marked as bounced: %s") % names)

        company = self.env.company
        journal = company.check_journal_id or self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', 'in', ('general', 'bank', 'cash'))
        ], limit=1)

        bounced_acc = company.check_bounced_account_id
        if not bounced_acc:
            bounced_acc = company.check_receivable_account_id

        financial_checks = self.check_ids.filtered(lambda c: not c.is_guarantee)

        for check in financial_checks:
            line_vals = []
            reason_label = dict(self._fields['bounce_reason'].selection).get(self.bounce_reason, self.bounce_reason)
            desc = _("ارتداد شيك رقم %s - سبب: %s") % (check.name, reason_label)

            if check.state == 'deposited':
                # Debit: Bounced Account / Partner Receivable
                # Credit: Under Collection Account
                under_col_acc = company.check_under_collection_account_id
                debit_acc = bounced_acc or check.partner_id.property_account_receivable_id
                line_vals = [
                    {
                        'name': desc,
                        'account_id': debit_acc.id,
                        'partner_id': check.partner_id.id,
                        'debit': check.amount,
                        'credit': 0.0,
                    },
                    {
                        'name': _("إلغاء شيك برسم التحصيل رقم %s بسبب الارتداد") % check.name,
                        'account_id': under_col_acc.id if under_col_acc else debit_acc.id,
                        'debit': 0.0,
                        'credit': check.amount,
                    }
                ]
            elif check.state == 'endorsed':
                # The third party returned the check to us!
                curr_partner_acc = (
                    check.current_partner_id.property_account_payable_id
                    or check.current_partner_id.property_account_receivable_id
                )
                orig_partner_acc = (
                    check.partner_id.property_account_receivable_id
                    or bounced_acc
                )
                line_vals = [
                    {
                        'name': _("مطالبة بقيمة الشيك المظهر المرتد رقم %s من الطرف الأصلي") % check.name,
                        'account_id': orig_partner_acc.id,
                        'partner_id': check.partner_id.id,
                        'debit': check.amount,
                        'credit': 0.0,
                    },
                    {
                        'name': _("إعادة فتح استحقاق الطرف المظهر له %s للشيك المرتد %s") % (check.current_partner_id.name, check.name),
                        'account_id': curr_partner_acc.id,
                        'partner_id': check.current_partner_id.id,
                        'debit': 0.0,
                        'credit': check.amount,
                    }
                ]
            else:
                # in_safe or draft
                rec_acc = company.check_receivable_account_id
                line_vals = [
                    {
                        'name': desc,
                        'account_id': bounced_acc.id,
                        'partner_id': check.partner_id.id,
                        'debit': check.amount,
                        'credit': 0.0,
                    },
                    {
                        'name': _("إلغاء أوراق قبض شيك رقم %s") % check.name,
                        'account_id': rec_acc.id if rec_acc else bounced_acc.id,
                        'partner_id': check.partner_id.id,
                        'debit': 0.0,
                        'credit': check.amount,
                    }
                ]

            move = False
            if line_vals and journal:
                move = self.env['account.move'].create({
                    'move_type': 'entry',
                    'date': self.bounce_date,
                    'journal_id': journal.id,
                    'ref': _("قيد ارتداد شيك - %s") % check.name,
                    'line_ids': [(0, 0, lv) for lv in line_vals],
                })
                move.action_post()

            vals = {
                'state': 'bounced',
                'bounce_date': self.bounce_date,
                'bounce_reason': f"{reason_label} - {self.notes or ''}".strip(' -'),
            }
            if move:
                vals['move_ids'] = [(4, move.id)]
            check.write(vals)

        return {'type': 'ir.actions.act_window_close'}
