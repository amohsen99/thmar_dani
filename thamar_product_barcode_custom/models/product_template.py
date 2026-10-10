from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    thamar_barcode_mode = fields.Selection(
        related="categ_id.thamar_barcode_mode",
        string="طريقة التكويد",
        readonly=True,
    )
    thamar_barcode_preview = fields.Char(
        string="نموذج الكود",
        compute="_compute_thamar_barcode_preview",
    )

    @api.depends(
        "categ_id.thamar_full_category_code",
        "categ_id.thamar_barcode_mode",
        "categ_id.thamar_barcode_serial_digits",
    )
    def _compute_thamar_barcode_preview(self):
        for template in self:
            category = template.categ_id
            if not category or category.thamar_barcode_mode == "none":
                template.thamar_barcode_preview = False
            elif category.thamar_barcode_mode == "fixed":
                template.thamar_barcode_preview = category.thamar_full_category_code
            else:
                template.thamar_barcode_preview = "%s%s" % (
                    category.thamar_full_category_code,
                    "0" * category.thamar_barcode_serial_digits,
                )

    def write(self, vals):
        if "categ_id" in vals:
            new_category = self.env["product.category"].browse(vals["categ_id"])
            for template in self:
                generated = template.product_variant_ids.filtered(
                    "thamar_barcode_category_id"
                )
                if generated and any(
                    product.thamar_barcode_category_id != new_category
                    for product in generated
                ):
                    raise ValidationError(
                        _(
                            "Product category cannot be changed after a category barcode has been generated for %(product)s.",
                            product=template.display_name,
                        )
                    )

        result = super().write(vals)
        if "categ_id" in vals:
            self.product_variant_ids._thamar_assign_category_barcodes()
        return result

    def action_generate_thamar_category_barcodes(self):
        self.product_variant_ids._thamar_assign_category_barcodes()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Product Coding"),
                "message": _("Missing category barcodes were generated successfully."),
                "type": "success",
                "sticky": False,
            },
        }
