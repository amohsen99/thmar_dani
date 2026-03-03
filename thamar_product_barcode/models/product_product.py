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

    # Removed onchange warning - will use wizard confirmation instead

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
        # Store old category for comparison
        old_categories = {}
        if 'categ_id' in vals:
            for product in self:
                old_categories[product.id] = product.categ_id.id if product.categ_id else False

        result = super().write(vals)

        # Check if category changed for category_sequence strategy
        if 'categ_id' in vals:
            for product in self:
                if (product.product_tmpl_id.auto_generate_barcode and
                    product.barcode):
                    # Only regenerate if category actually changed
                    old_categ_id = old_categories.get(product.id)
                    new_categ_id = product.categ_id.id if product.categ_id else False
                    if old_categ_id != new_categ_id:
                        # Regenerate barcode with new category and next sequence
                        old_barcode = product.barcode
                        product._regenerate_barcode_on_category_change()
                        _logger.info(
                            f"Category changed for product {product.id}: "
                            f"Barcode updated from {old_barcode} to {product.barcode}"
                        )

        if any(field in vals for field in ['product_template_attribute_value_ids']):
            for product in self:
                if product.product_tmpl_id.auto_generate_barcode:
                    product._generate_barcode()

        return result

    def _regenerate_barcode_on_category_change(self):
        """
        Regenerate barcode when category changes (for category_sequence strategy)
        Generates a NEW barcode with the new category prefix and NEXT sequence number
        """
        self.ensure_one()

        if not self.barcode:
            return

        old_barcode = self.barcode

        log_lines = [f"=== Regenerating Barcode on Category Change for {self.name} ==="]
        log_lines.append(f"Old Barcode: {old_barcode}")
        log_lines.append(f"New Category: {self.categ_id.complete_name if self.categ_id else 'None'}")

        try:
            # Generate new barcode with next sequence from new category
            new_barcode, strategy_log_lines = self._generate_category_sequence_barcode()
            log_lines.extend(strategy_log_lines)

            if new_barcode:
                # Check for duplicates
                existing = self.search([
                    ('barcode', '=', new_barcode),
                    ('id', '!=', self.id)
                ], limit=1)

                if existing:
                    log_lines.append(f"ERROR: Duplicate barcode found for {existing.display_name}")
                    self.barcode_generation_log = '\n'.join(log_lines)

                    raise UserError(_(
                        "⚠️ BARCODE REGENERATION FAILED - DUPLICATE EXISTS\n\n"
                        "Cannot regenerate barcode because it would create a duplicate:\n\n"
                        "New Barcode: %s\n"
                        "Already used by: %s\n"
                        "  • Internal Reference: %s\n"
                        "  • Category: %s\n\n"
                        "Please regenerate the barcode manually."
                    ) % (
                        new_barcode,
                        existing.display_name,
                        existing.default_code or 'N/A',
                        existing.categ_id.name or 'N/A'
                    ))

                # Update barcode
                self.barcode = new_barcode
                log_lines.append(f"New Barcode: {new_barcode}")
                log_lines.append("✅ SUCCESS: Barcode regenerated with new category sequence")
                self.barcode_generation_log = '\n'.join(log_lines)

                _logger.info(
                    f"Barcode regenerated for product {self.id} due to category change: "
                    f"{old_barcode} -> {new_barcode}"
                )
            else:
                log_lines.append("WARNING: Failed to generate new barcode")
                self.barcode_generation_log = '\n'.join(log_lines)

        except UserError:
            raise
        except Exception as e:
            log_lines.append(f"ERROR: {str(e)}")
            self.barcode_generation_log = '\n'.join(log_lines)
            _logger.error(f"Error regenerating barcode for product {self.id}: {e}")
            raise UserError(_(
                "Failed to regenerate barcode after category change: %s\n\n"
                "Please check the barcode generation log for details."
            ) % str(e))

    def _get_category_barcode_code(self):
        """
        Get category barcode code, including parent categories
        Returns only the first found code (for backward compatibility)
        """
        self.ensure_one()

        if not self.categ_id:
            return None

        # If current category has a barcode code, use it
        if self.categ_id.barcode_code:
            return self.categ_id.barcode_code

        # Otherwise, look for parent categories
        parent_category = self.categ_id.parent_id
        while parent_category:
            if parent_category.barcode_code:
                return parent_category.barcode_code
            parent_category = parent_category.parent_id

        return None

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
            return '00'

        # Combine all codes
        return ''.join(codes)

    def _generate_category_sequence_barcode(self):
        """
        Generate barcode using hierarchical category + sequence (13 characters total)
        Format: CATEGORYPREFIX + SEQUENCE = 13 characters
        Example: CHSV000000001 (CHSV = 4 chars, 000000001 = 9 chars)
        """
        self.ensure_one()

        log_lines = [f"=== Category+Sequence Barcode Generation for {self.name} ==="]

        try:
            # Get hierarchical category code (combines parent + child codes)
            category_code = self._get_hierarchical_category_code()
            log_lines.append(f"Hierarchical Category Code: {category_code}")

            # Fixed padding for simplified format: [PREFIX]-[5 DIGITS]
            sequence_padding = 5
            log_lines.append(f"Prefix: {category_code}, Sequence Padding: {sequence_padding}")

            # Get or create sequence for this category
            sequence_code = f'product.barcode.{category_code}'
            sequence = self.env['ir.sequence'].search([
                ('code', '=', sequence_code),
                ('company_id', 'in', [False, self.company_id.id])
            ], order='company_id', limit=1)

            if not sequence:
                # Create new sequence for this category
                sequence = self.env['ir.sequence'].create({
                    'name': f'Product Barcode Sequence - {category_code}',
                    'code': sequence_code,
                    'prefix': f'{category_code}-',
                    'padding': sequence_padding,
                    'number_next': 1,
                    'number_increment': 1,
                    'company_id': self.company_id.id or False,
                })
                log_lines.append(f"✅ Created new sequence: {sequence.name}")
                log_lines.append(f"   Code: {sequence_code}")
                log_lines.append(f"   Prefix: {category_code}")
                log_lines.append(f"   Padding: {sequence_padding}")
            else:
                log_lines.append(f"✅ Using existing sequence: {sequence.name}")

                # Update sequence padding and prefix for simplified format
                if sequence.padding != sequence_padding or sequence.prefix != f'{category_code}-':
                    sequence.write({
                        'prefix': f'{category_code}-',
                        'padding': sequence_padding,
                    })
                    log_lines.append(f"   Updated sequence prefix to: {category_code}-")
                    log_lines.append(f"   Updated sequence padding to: {sequence_padding}")

            # Generate the barcode
            barcode = sequence.next_by_id()
            log_lines.append(f"✅ Generated Barcode: {barcode} (Length: {len(barcode)})")

            return barcode, log_lines

        except UserError:
            raise
        except Exception as e:
            log_lines.append(f"❌ ERROR in category+sequence generation: {str(e)}")
            raise UserError(_(
                "Failed to generate barcode: %s\n\n"
                "Please check the barcode generation log for details."
            ) % str(e))

    def _generate_barcode(self):
        """
        Generate barcode using standardized sequence format.
        """
        self.ensure_one()
        log_lines = [f"=== Barcode Generation for {self.name} ==="]

        try:
            barcode, strategy_log_lines = self._generate_category_sequence_barcode()
            log_lines.extend(strategy_log_lines)

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
                error_details.append("")
                error_details.append(_("Please contact administrator as this is a sequence conflict."))

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
                        'message': _('Barcode generated successfully!\n\nBarcode: %s') % (
                            self.barcode
                        ),
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
                      'Please check the generation log for details.') % (
                        self.display_name,
                        str(e)
                    )
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
                    error_products.append(f"{product.display_name} ({str(e)[:50]}...)")
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