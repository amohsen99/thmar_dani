# -*- coding: utf-8 -*-
from odoo import models, fields, api

try:
    from num2words import num2words
except ImportError:
    num2words = None


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Cheque/Bank fields
    bank_id = fields.Many2one(
        'res.bank',
        string='Bank',
        help='Bank for cheque payment'
    )
    cheque_due_date = fields.Date(
        string='Cheque Due Date',
        help='Due date for cheque payment'
    )
    cheque_number = fields.Char(
        string='Cheque Number',
        help='Cheque number for payment'
    )

    def amount_to_text_arabic(self):
        """
        Convert amount to Arabic text
        Returns the amount in Arabic words
        """
        self.ensure_one()
        
        if num2words is None:
            return ""
        
        # Get the amount
        amount = self.amount
        
        # Split into integer and decimal parts
        integral = int(amount)
        fractional = int(round((amount - integral) * 100))
        
        # Get currency labels
        currency_unit = 'جنيه'
        currency_subunit ='قرش'
        
        # Convert to Arabic words
        try:
            # Convert integer part to Arabic
            integral_text = num2words(integral, lang='ar')
            
            if fractional > 0:
                # Convert fractional part to Arabic
                fractional_text = num2words(fractional, lang='ar')
                result = f"{integral_text} {currency_unit} و {fractional_text} {currency_subunit}"
            else:
                result = f"{integral_text} {currency_unit}"
            
            return result
            
        except Exception:
            # Fallback to English if Arabic fails
            return self.currency_id.amount_to_text(amount)
    
    def amount_to_text_with_lang(self):
        """
        Convert amount to text based on user's language
        """
        self.ensure_one()
        
        # Get user's language
        lang_code = self.env.user.lang or 'en_US'

        # If Arabic, use Arabic conversion
        if lang_code.startswith('ar'):
            return self.amount_to_text_arabic()
        else:
            # Use default Odoo conversion
            return self.currency_id.amount_to_text(self.amount)

