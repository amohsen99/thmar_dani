# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    barcode_position = fields.Selection([
        ('color', 'Color (4 chars)'),
        ('design', 'Design (4 chars)'),
        ('grade', 'Grade (1 char)'),
        ('type', 'Type (1 char)'),
    ], string='Barcode Position',
       help='Position of this attribute in the barcode structure')


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'
    _rec_names_search = ['name', 'barcode_code']



    barcode_code = fields.Char(
        string='Barcode Code',
        help='Code used in barcode generation'
    )
    notes = fields.Char(
        string="Notes",
        help="Additional notes about this color/attribute value"
    )
    customer_id = fields.Char(
        string="Customer",
        help="Customer or source associated with this color/attribute value"
    )

    @api.constrains('barcode_code', 'attribute_id')
    def _check_barcode_code(self):
        """Validate barcode code uniqueness within same attribute"""
        for value in self:
            if value.barcode_code:
                # Check uniqueness within same attribute
                duplicate = self.search([
                    ('barcode_code', '=', value.barcode_code),
                    ('attribute_id', '=', value.attribute_id.id),
                    ('id', '!=', value.id)
                ], limit=1)
                
                if duplicate:
                    raise ValidationError(
                        f'Barcode Code "{value.barcode_code}" is already used by value "{duplicate.name}" '
                        f'in attribute "{value.attribute_id.name}".'
                    )



