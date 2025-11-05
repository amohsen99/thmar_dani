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
        
        # Check if variant attributes changed
        if any(key.startswith('product_template_attribute_value') for key in vals.keys()):
            for product in self:
                if product.product_tmpl_id.auto_generate_barcode:
                    product._generate_barcode()
        
        # Check if category changed
        if 'categ_id' in vals:
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
        
        log_lines = []
        log_lines.append(f"=== Barcode Generation for {self.name} ===")
        
        try:
            # Get category code
            if not self.categ_id:
                log_lines.append("ERROR: No category set")
                self.barcode_generation_log = '\n'.join(log_lines)
                return
            
            if not self.categ_id.barcode_code:
                log_lines.append(f"ERROR: Category '{self.categ_id.name}' has no barcode code")
                self.barcode_generation_log = '\n'.join(log_lines)
                return
            
            category_code = self.categ_id.barcode_code
            log_lines.append(f"Category Code: {category_code}")
            
            # Get variant attribute values
            variant_values = self.product_template_attribute_value_ids.mapped('product_attribute_value_id')
            
            # Initialize barcode parts
            barcode_parts = {
                'category': category_code,
                'color': None,
                'design': None,
                'grade': None,
                'type': None,
            }
            
            # Extract codes from variant values
            for value in variant_values:
                if not value.attribute_id.barcode_position:
                    continue
                
                position = value.attribute_id.barcode_position
                code = value.barcode_code
                
                if not code:
                    log_lines.append(f"WARNING: {value.attribute_id.name} value '{value.name}' has no barcode code")
                    continue
                
                barcode_parts[position] = code
                log_lines.append(f"{position.title()} Code: {code} ({value.name})")
            
            # Check if all required parts are present
            missing_parts = []
            for part, value in barcode_parts.items():
                if part != 'category' and value is None:
                    missing_parts.append(part)
            
            if missing_parts:
                log_lines.append(f"ERROR: Missing barcode codes for: {', '.join(missing_parts)}")
                self.barcode_generation_log = '\n'.join(log_lines)
                return
            
            # Generate barcode
            barcode = (
                barcode_parts['category'] +
                barcode_parts['color'] +
                barcode_parts['design'] +
                barcode_parts['grade'] +
                barcode_parts['type']
            )
            
            log_lines.append(f"Generated Barcode: {barcode}")
            log_lines.append(f"Structure: {category_code}|{barcode_parts['color']}|{barcode_parts['design']}|{barcode_parts['grade']}|{barcode_parts['type']}")
            
            # Check if barcode already exists
            existing = self.search([
                ('barcode', '=', barcode),
                ('id', '!=', self.id)
            ], limit=1)
            
            if existing:
                log_lines.append(f"WARNING: Barcode {barcode} already exists for product {existing.name}")
                log_lines.append("Barcode NOT updated to avoid duplicates")
            else:
                self.barcode = barcode
                log_lines.append("SUCCESS: Barcode updated")
            
        except Exception as e:
            log_lines.append(f"ERROR: {str(e)}")
            _logger.error(f"Error generating barcode for product {self.id}: {e}")
        
        finally:
            self.barcode_generation_log = '\n'.join(log_lines)

    def action_regenerate_barcode(self):
        """Manual action to regenerate barcode"""
        for product in self:
            if not product.product_tmpl_id.auto_generate_barcode:
                raise UserError(
                    _('Auto Generate Barcode is disabled for this product. '
                      'Enable it first in the product template.')
                )
            product._generate_barcode()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Barcode Generated'),
                'message': _('Barcode has been regenerated for %s product(s)') % len(self),
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_barcode_breakdown(self):
        """Get breakdown of barcode components for display"""
        self.ensure_one()
        if not self.barcode or len(self.barcode) < 12:
            return {}
        
        return {
            'category': self.barcode[0:2],
            'color': self.barcode[2:6],
            'design': self.barcode[6:10],
            'grade': self.barcode[10:11],
            'type': self.barcode[11:12],
        }

