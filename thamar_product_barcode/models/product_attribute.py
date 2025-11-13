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
        """Validate barcode code based on attribute position"""
        for value in self:
            if value.barcode_code and value.attribute_id.barcode_position:
                position = value.attribute_id.barcode_position
                code = value.barcode_code
                
                # Check length based on position
                if position in ['color', 'design']:
                    if len(code) != 4:
                        raise ValidationError(
                            f'{position.title()} code must be exactly 4 characters long. '
                            f'Current: "{code}" ({len(code)} chars)'
                        )
                    # if not code.isdigit():
                    #     raise ValidationError(
                    #         f'{position.title()} code must contain only digits (0-9).'
                    #     )
                
                elif position in ['grade', 'type']:
                    if len(code) != 1:
                        raise ValidationError(
                            f'{position.title()} code must be exactly 1 character long. '
                            f'Current: "{code}" ({len(code)} chars)'
                        )
                    # if position == 'grade' and not code.isdigit():
                    #     raise ValidationError(
                    #         'Grade code must be a digit (0-9).'
                    #     )
                    # if position == 'type' and not code.isalpha():
                    #     raise ValidationError(
                    #         'Type code must be a letter (e.g., P for Printing, D for Drying).'
                    #     )
                
                # Check uniqueness within same attribute
                duplicate = self.search([
                    ('barcode_code', '=', code),
                    ('attribute_id', '=', value.attribute_id.id),
                    ('id', '!=', value.id)
                ], limit=1)
                
                if duplicate:
                    raise ValidationError(
                        f'Barcode Code "{code}" is already used by value "{duplicate.name}" '
                        f'in attribute "{value.attribute_id.name}".'
                    )

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=None, order=None):
        """Allow searching by barcode code"""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('barcode_code', operator, name)] + domain
        return super()._name_search(name='', domain=domain, operator=operator, limit=limit, order=order)

