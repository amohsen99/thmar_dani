# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    barcode_code = fields.Char(
        string='Barcode Code',
        help='character code used in barcode generation (e.g., ac, bd, df)'
    )

    @api.constrains('barcode_code')
    def _check_barcode_code(self):
        """Validate barcode code format and uniqueness"""
        for category in self:
            if category.barcode_code:
                # Check length
                # if len(category.barcode_code) != 2:
                #     raise ValidationError(
                #         'Barcode Code must be exactly 2 characters long.'
                #     )
                
                # Check if only digits
                # if not category.barcode_code.isdigit():
                #     raise ValidationError(
                #         ' Barcode Code must contain only digits (0-9).'
                #     )
                
                # Check uniqueness
                duplicate = self.search([
                    ('barcode_code', '=', category.barcode_code),
                    ('id', '!=', category.id)
                ], limit=1)
                
                if duplicate:
                    raise ValidationError(
                        f'Barcode Code "{category.barcode_code}" is already used by category "{duplicate.name}".'
                    )

