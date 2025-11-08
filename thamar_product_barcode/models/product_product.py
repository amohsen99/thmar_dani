# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    barcode_generation_log = fields.Text(
        string='Barcode Generation Log',
        readonly=True,
        help='Log of barcode generation process'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Generate barcode on product variant creation"""
        products = super().create(vals_list)
        for product in products:
            if product.product_tmpl_id.auto_generate_barcode:
                product._generate_barcode()
        return products

    def write(self, vals):
        """Regenerate barcode if relevant fields change"""
        result = super().write(vals)

        # Check if variant attributes or category changed
        if any(key.startswith('product_template_attribute_value') for key in vals.keys()) or 'categ_id' in vals:
            for product in self:
                if product.product_tmpl_id.auto_generate_barcode:
                    product._generate_barcode()

        return result

    def _generate_barcode(self):
        """
        Generate barcode from category and variant attributes
        Structure: CATEGORYCOLORDESIGNGRADETYP
        Example: 01000100011P
        """
        self.ensure_one()

        log_lines = [f"=== Barcode Generation for {self.name} ==="]

        try:
            # --- CATEGORY CODE ---
            if not self.categ_id:
                raise UserError(_("No category is set for this product."))

            if not self.categ_id.barcode_code:
                raise UserError(_("Category '%s' has no barcode code.") % self.categ_id.name)

            category_code = self.categ_id.barcode_code
            log_lines.append(f"Category Code: {category_code}")

            # --- VARIANT ATTRIBUTE VALUES ---
            variant_values = self.product_template_attribute_value_ids.mapped('product_attribute_value_id')

            barcode_parts = {
                'category': category_code,
                'color': None,
                'design': None,
                'grade': None,
                'type': None,
            }

            for value in variant_values:
                position = value.attribute_id.barcode_position
                code = value.barcode_code
                if not position or not code:
                    continue
                barcode_parts[position] = code
                log_lines.append(f"{position.title()} Code: {code} ({value.name})")

            # Fill missing parts with default codes
            for part, value in barcode_parts.items():
                if part != 'category' and value is None:
                    default = '0000' if part in ['color', 'design'] else '0'
                    barcode_parts[part] = default
                    log_lines.append(f"{part.title()} Code: {default} (default)")

            # --- BARCODE GENERATION ---
            barcode = (
                barcode_parts['category'] +
                barcode_parts['color'] +
                barcode_parts['design'] +
                barcode_parts['grade'] +
                barcode_parts['type']
            )

            log_lines.append(f"Generated Barcode: {barcode}")

            # --- DUPLICATE CHECK ---
            existing = self.search([
                ('barcode', '=', barcode),
                ('id', '!=', self.id)
            ], limit=1)

            if existing:
                log_lines.append(f"ERROR: Duplicate barcode found for {existing.display_name}")
                self.barcode_generation_log = '\n'.join(log_lines)

                # Build detailed error message
                error_details = []
                error_details.append(_("⚠️ BARCODE ALREADY EXISTS"))
                error_details.append("")
                error_details.append(_("Barcode: %s") % barcode)
                error_details.append("")
                error_details.append(_("This barcode is already used by:"))
                error_details.append(_("  • Product: %s") % existing.display_name)
                error_details.append(_("  • Internal Reference: %s") % (existing.default_code or 'N/A'))
                error_details.append(_("  • Category: %s") % (existing.categ_id.name or 'N/A'))

                # Show variant attributes if available
                if existing.product_template_attribute_value_ids:
                    error_details.append("")
                    error_details.append(_("Variant Attributes:"))
                    for ptav in existing.product_template_attribute_value_ids:
                        attr_value = ptav.product_attribute_value_id
                        error_details.append(_("  • %s: %s") % (attr_value.attribute_id.name, attr_value.name))

                error_details.append("")
                error_details.append(_("Please change the variant attributes or category to generate a unique barcode."))

                raise UserError('\n'.join(error_details))

            # --- UPDATE BARCODE ---
            self.barcode = barcode
            log_lines.append("SUCCESS: Barcode updated successfully")
            self.barcode_generation_log = '\n'.join(log_lines)

            _logger.info(f"Barcode generated successfully for product {self.id}: {barcode}")
            return True

        except UserError as ue:
            log_lines.append(f"USER ERROR: {str(ue)}")
            self.barcode_generation_log = '\n'.join(log_lines)
            raise

        except Exception as e:
            log_lines.append(f"ERROR: {str(e)}")
            self.barcode_generation_log = '\n'.join(log_lines)
            _logger.error(f"Error generating barcode for product {self.id}: {e}")
            return False

    def action_regenerate_barcode(self):
        """Manual action to regenerate barcode"""
        # Check if auto-generate is enabled for all products
        for product in self:
            if not product.product_tmpl_id.auto_generate_barcode:
                raise UserError(
                    _('⚠️ Auto Generate Barcode is disabled!\n\n'
                      'Product: %s\n\n'
                      'Please enable "Auto Generate Barcode" in the product template first.') % product.display_name
                )

        # If single product, raise UserError on failure for detailed error message
        if len(self) == 1:
            try:
                self._generate_barcode()
                # Show success toast
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('✅ Success'),
                        'message': _('Barcode generated successfully!\n\nBarcode: %s') % self.barcode,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except UserError as e:
                # Re-raise UserError to show detailed error dialog
                raise
            except Exception as e:
                raise UserError(
                    _('❌ Error generating barcode\n\n'
                      'Product: %s\n\n'
                      'Error: %s\n\n'
                      'Please check the generation log for details.') % (self.display_name, str(e))
                )

        # For multiple products, collect results and show summary
        else:
            success_count = 0
            fail_count = 0
            error_products = []

            for product in self:
                try:
                    if product._generate_barcode():
                        success_count += 1
                    else:
                        fail_count += 1
                        error_products.append(product.display_name)
                except UserError as e:
                    fail_count += 1
                    error_products.append(f"{product.display_name} (duplicate)")
                except Exception as e:
                    fail_count += 1
                    error_products.append(product.display_name)

            # Show appropriate notification based on results
            if success_count > 0 and fail_count == 0:
                # All successful
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('✅ Batch Generation Successful'),
                        'message': _('Successfully generated barcodes for %s product(s)!') % success_count,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            elif success_count > 0 and fail_count > 0:
                # Partial success
                error_list = '\n'.join([f"  • {p}" for p in error_products[:5]])
                if len(error_products) > 5:
                    error_list += f"\n  • ... and {len(error_products) - 5} more"

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('⚠️ Partial Success'),
                        'message': _('Generated: %s\nFailed: %s\n\nFailed products:\n%s') % (
                            success_count, fail_count, error_list
                        ),
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            else:
                # All failed
                error_list = '\n'.join([f"  • {p}" for p in error_products[:5]])
                if len(error_products) > 5:
                    error_list += f"\n  • ... and {len(error_products) - 5} more"

                raise UserError(
                    _('❌ Barcode Generation Failed\n\n'
                      'Failed to generate barcodes for all %s selected product(s).\n\n'
                      'Failed products:\n%s\n\n'
                      'Please check the generation logs for details.') % (fail_count, error_list)
                )
