from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    thamar_barcode_category_id = fields.Many2one(
        comodel_name="product.category",
        string="فئة التكويد",
        copy=False,
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    thamar_barcode_serial = fields.Char(
        string="مسلسل التكويد",
        copy=False,
        readonly=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products._thamar_assign_category_barcodes()
        return products

    def write(self, vals):
        if not self.env.context.get("thamar_category_barcode_assignment"):
            protected = {"barcode", "default_code"}.intersection(vals)
            if protected:
                for product in self.filtered("thamar_barcode_category_id"):
                    changed = any(
                        vals[field_name] != product[field_name]
                        for field_name in protected
                    )
                    if changed:
                        raise ValidationError(
                            _(
                                "The generated barcode and internal reference are protected for product %(product)s.",
                                product=product.display_name,
                            )
                        )
        return super().write(vals)

    def _thamar_code_is_used(self, code):
        self.ensure_one()
        return bool(
            self.sudo().search_count(
                [
                    ("id", "!=", self.id),
                    "|",
                    ("barcode", "=", code),
                    ("default_code", "=", code),
                ],
                limit=1,
            )
        )

    def _thamar_next_available_code(self, category):
        self.ensure_one()
        prefix = category.thamar_full_category_code
        if category.thamar_barcode_mode == "fixed":
            if self._thamar_code_is_used(prefix):
                raise ValidationError(
                    _(
                        "Fixed code %(code)s is already used. A fixed-code category can be assigned to one product variant only.",
                        code=prefix,
                    )
                )
            return prefix, False

        sequence = category._thamar_get_barcode_sequence()
        for _attempt in range(1000):
            serial = sequence.next_by_id()
            code = prefix + serial
            if not self._thamar_code_is_used(code):
                return code, serial
        raise ValidationError(
            _("Could not find an available product code after 1000 attempts."))

    def _thamar_assign_category_barcodes(self):
        for product in self:
            if product.thamar_barcode_category_id:
                continue
            category = product.categ_id
            if not category or category.thamar_barcode_mode == "none":
                continue

            code, serial = product._thamar_next_available_code(category)
            product.with_context(thamar_category_barcode_assignment=True).write(
                {
                    "barcode": code,
                    "default_code": code,
                    "thamar_barcode_category_id": category.id,
                    "thamar_barcode_serial": serial,
                }
            )
        return True
