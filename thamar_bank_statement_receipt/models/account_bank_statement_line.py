# -*- coding: utf-8 -*-
from odoo import models

try:
    from num2words import num2words
except ImportError:
    num2words = None


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

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
