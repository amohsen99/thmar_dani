# -*- coding: utf-8 -*-
from odoo import models, fields, api

try:
    from num2words import num2words
except ImportError:
    num2words = None


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    receipt_number = fields.Char(string='Receipt/Payment Number', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            amount = vals.get('amount', 0.0)
            if amount >= 0:
                vals['receipt_number'] = self.env['ir.sequence'].next_by_code('account.bank.statement.line.receipt')
            else:
                vals['receipt_number'] = self.env['ir.sequence'].next_by_code('account.bank.statement.line.payment')
        return super(AccountBankStatementLine, self).create(vals_list)

    def ensure_receipt_number(self):
        """Ensure the record has a receipt number, generating one if missing."""
        for record in self:
            if not record.receipt_number:
                if record.amount >= 0:
                    record.receipt_number = self.env['ir.sequence'].next_by_code('account.bank.statement.line.receipt')
                else:
                    record.receipt_number = self.env['ir.sequence'].next_by_code('account.bank.statement.line.payment')
        return True

    def amount_to_text_arabic(self):
        """Convert the absolute amount to Arabic words."""
        self.ensure_one()
        if num2words is None:
            return ""

        amount = abs(self.amount)
        integral = int(amount)
        fractional = int(round((amount - integral) * 100))

        currency_unit = 'جنيه'
        currency_subunit = 'قرش'

        try:
            integral_text = num2words(integral, lang='ar')
            if fractional > 0:
                fractional_text = num2words(fractional, lang='ar')
                return f"{integral_text} {currency_unit} و {fractional_text} {currency_subunit}"
            return f"{integral_text} {currency_unit}"
        except Exception:
            return self.currency_id.amount_to_text(amount)

    def amount_to_text_with_lang(self):
        """Return amount in words based on the active language."""
        self.ensure_one()
        lang_code = self.env.user.lang or 'en_US'
        if lang_code.startswith('ar'):
            return self.amount_to_text_arabic()
        return self.currency_id.amount_to_text(abs(self.amount))
