# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        """Find product variants from their attribute or attribute-value text.

        Product variants are linked to ``product.template.attribute.value``
        records, whose displayed value is a related/non-stored field. Resolve
        the matching records first, then search their linked variants. This
        makes the ``product_id`` autocomplete reliably find values such as
        ``Red``, ``XL``, or ``325``.
        """
        if not name:
            return super().name_search(name, domain=domain, operator=operator, limit=limit)

        attribute_values = self.env['product.template.attribute.value'].search(
            Domain('product_attribute_value_id.name', operator, name)
            | Domain('attribute_id.name', operator, name)
        )
        variant_results = []
        if attribute_values:
            variants = self.search_fetch(
                Domain(domain or Domain.TRUE)
                & Domain('product_template_attribute_value_ids', 'in', attribute_values.ids),
                ['display_name'],
                limit=limit,
            )
            variant_results = [(product.id, product.display_name) for product in variants.sudo()]

        # Keep Odoo's normal name/SKU/barcode results, without duplicating
        # variants found through their attribute values.
        remaining_limit = limit and limit - len(variant_results)
        if remaining_limit is not None and remaining_limit <= 0:
            return variant_results

        product_ids = {product_id for product_id, _display_name in variant_results}
        standard_results = super().name_search(
            name,
            domain=domain,
            operator=operator,
            limit=remaining_limit or 0,
        )
        return variant_results + [
            result for result in standard_results if result[0] not in product_ids
        ]
