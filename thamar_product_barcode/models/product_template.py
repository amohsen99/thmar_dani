# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    auto_generate_barcode = fields.Boolean(
        string='Auto Generate Barcode',
        default=True,
        help='Automatically generate barcode from category and variants'
    )

    barcode_preview = fields.Char(
        string='Barcode Preview',
        compute='_compute_barcode_preview',
        help='Preview of how the barcode will be generated'
    )

    @api.depends('categ_id', 'categ_id.barcode_code')
    def _compute_barcode_preview(self):
        """Show preview of barcode structure"""
        for template in self:
            if template.categ_id and template.categ_id.barcode_code:
                preview = f"{template.categ_id.barcode_code}[COLOR][DESIGN][GRADE][TYPE]"
                template.barcode_preview = preview
            else:
                template.barcode_preview = 'Set category with barcode code first'

    def _get_barcode_structure_info(self):
        """Get information about required attributes for barcode"""
        self.ensure_one()
        return {
            'category_code': self.categ_id.barcode_code if self.categ_id else None,
            'needs_color': True,
            'needs_design': True,
            'needs_grade': True,
            'needs_type': True,
        }

