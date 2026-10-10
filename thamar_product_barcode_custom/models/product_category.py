from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = "product.category"

    thamar_barcode_code = fields.Char(
        string="جزء كود الفئة",
        help="أرقام هذه الفئة فقط. يجمع النظام أكواد الآباء بالترتيب لتكوين مقدمة كود المنتج.",
    )
    thamar_full_category_code = fields.Char(
        string="كود الفئة الكامل",
        compute="_compute_thamar_full_category_code",
        recursive=True,
        store=True,
        readonly=True,
    )
    thamar_barcode_mode = fields.Selection(
        selection=[
            ("none", "فئة تجميعية فقط"),
            ("sequence", "مسلسل تلقائي"),
            ("fixed", "كود ثابت"),
        ],
        string="طريقة التكويد",
        required=True,
        default="none",
    )
    thamar_barcode_serial_digits = fields.Integer(
        string="عدد خانات المسلسل",
        default=4,
        help="عدد خانات المسلسل الذي يضاف بعد كود الفئة الكامل.",
    )
    thamar_barcode_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="مسلسل التكويد",
        copy=False,
        readonly=True,
        ondelete="set null",
    )

    @api.depends("thamar_barcode_code", "parent_id.thamar_full_category_code")
    def _compute_thamar_full_category_code(self):
        for category in self:
            parent_code = category.parent_id.thamar_full_category_code or ""
            category.thamar_full_category_code = parent_code + (category.thamar_barcode_code or "")

    @api.constrains(
        "thamar_barcode_code",
        "thamar_barcode_mode",
        "thamar_barcode_serial_digits",
        "parent_id",
    )
    def _check_thamar_barcode_configuration(self):
        for category in self:
            code = category.thamar_barcode_code or ""
            if code and not code.isdigit():
                raise ValidationError(_("Category code parts must contain digits only."))

            if category.thamar_barcode_mode != "none" and not category.thamar_full_category_code:
                raise ValidationError(_("A coding category must have a numeric category code."))

            if (
                category.thamar_barcode_mode == "sequence"
                and not 1 <= category.thamar_barcode_serial_digits <= 12
            ):
                raise ValidationError(_("Serial digits must be between 1 and 12."))

            if code:
                duplicate = self.search(
                    [
                        ("id", "!=", category.id),
                        ("parent_id", "=", category.parent_id.id),
                        ("thamar_barcode_code", "=", code),
                    ],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError(
                        _(
                            "Category code %(code)s is already used by %(category)s under the same parent.",
                            code=code,
                            category=duplicate.display_name,
                        )
                    )

    def write(self, vals):
        protected_fields = {
            "parent_id",
            "thamar_barcode_code",
            "thamar_barcode_mode",
            "thamar_barcode_serial_digits",
        }
        if protected_fields.intersection(vals):
            descendants = self.search([("id", "child_of", self.ids)])
            used_product = self.env["product.product"].sudo().search(
                [("thamar_barcode_category_id", "in", descendants.ids)],
                limit=1,
            )
            if used_product:
                raise ValidationError(
                    _(
                        "The coding setup cannot be changed because it has already generated product %(product)s.",
                        product=used_product.display_name,
                    )
                )

        result = super().write(vals)
        if "thamar_barcode_serial_digits" in vals:
            for category in self.filtered("thamar_barcode_sequence_id"):
                category.thamar_barcode_sequence_id.sudo().write(
                    {"padding": category.thamar_barcode_serial_digits}
                )
        return result

    def _thamar_get_barcode_sequence(self):
        self.ensure_one()
        if self.thamar_barcode_mode != "sequence":
            return self.env["ir.sequence"]

        # Lock the category row so simultaneous product creation cannot create two sequences.
        self.env.cr.execute(
            "SELECT id FROM product_category WHERE id = %s FOR UPDATE",
            [self.id],
        )
        self.invalidate_recordset(["thamar_barcode_sequence_id"])
        if not self.thamar_barcode_sequence_id:
            sequence = self.env["ir.sequence"].sudo().create(
                {
                    "name": _("Product coding: %s", self.complete_name),
                    "code": "thamar_product_barcode_custom.category.%s" % self.id,
                    "implementation": "no_gap",
                    "padding": self.thamar_barcode_serial_digits,
                    "number_increment": 1,
                    "company_id": False,
                }
            )
            self.sudo().write({"thamar_barcode_sequence_id": sequence.id})
        return self.thamar_barcode_sequence_id.sudo()
