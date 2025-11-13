# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


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

    barcode_generation_strategy = fields.Selection([
        ('category_sequence', 'Category + Sequence'),
        ('variant_attributes', 'Variant Attributes')
    ], string='Barcode Generation Strategy', default='category_sequence',
       help="Choose how barcodes should be generated")

    # Removed onchange warning - category changes will auto-regenerate barcodes

    def write(self, vals):
        """Handle category changes for product templates"""
        # Store old categories for comparison
        old_categories = {}
        if 'categ_id' in vals:
            for template in self:
                old_categories[template.id] = template.categ_id.id if template.categ_id else False

        result = super().write(vals)

        # If category changed, regenerate barcodes for all variants
        if 'categ_id' in vals:
            for template in self:
                if template.auto_generate_barcode:
                    old_categ_id = old_categories.get(template.id)
                    new_categ_id = template.categ_id.id if template.categ_id else False

                    if old_categ_id != new_categ_id:
                        # Regenerate barcodes for all variants with existing barcodes
                        for variant in template.product_variant_ids.filtered(lambda v: v.barcode):
                            if template.barcode_generation_strategy == 'category_sequence':
                                variant._regenerate_barcode_on_category_change()
                            elif template.barcode_generation_strategy == 'variant_attributes':
                                variant._generate_barcode()

        return result

    @api.depends('categ_id', 'categ_id.barcode_code', 'categ_id.parent_id', 'barcode_generation_strategy')
    def _compute_barcode_preview(self):
        """Show preview of barcode structure based on selected strategy"""
        for template in self:
            strategy = template.barcode_generation_strategy

            if strategy == 'category_sequence':
                # Get hierarchical category code
                category_code = template._get_hierarchical_category_code()
                if category_code:
                    # Calculate sequence length
                    prefix_length = len(category_code)
                    sequence_length = 13 - prefix_length
                    sequence_preview = '0' * sequence_length
                    preview = f"{category_code}{sequence_preview} (13 chars: {prefix_length} prefix + {sequence_length} sequence)"
                    template.barcode_preview = preview
                else:
                    template.barcode_preview = 'Set category with barcode code first'
            else:  # variant_attributes
                if template.categ_id and template.categ_id.barcode_code:
                    preview = f"{template.categ_id.barcode_code}[COLOR][DESIGN][GRADE][TYPE]"
                    template.barcode_preview = preview
                else:
                    template.barcode_preview = 'Set category with barcode code first'

    def _get_hierarchical_category_code(self):
        """
        Get hierarchical category barcode code by combining parent and child codes
        Example: If parent is "CH" and child is "SV", returns "CHSV"
        """
        self.ensure_one()

        if not self.categ_id:
            return None

        # Collect all category codes from root to current category
        codes = []
        current_category = self.categ_id

        while current_category:
            if current_category.barcode_code:
                codes.insert(0, current_category.barcode_code)  # Insert at beginning
            current_category = current_category.parent_id

        if not codes:
            return None

        # Combine all codes
        return ''.join(codes)

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

