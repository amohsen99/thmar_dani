# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WeavingYarnLine(models.Model):
    _name = "thamar.weaving.yarn.line"
    _description = "Weaving Yarn Consumption Line"
    _order = "order_id, id"

    order_id = fields.Many2one(
        "thamar.weaving.order",
        string="أمر تشغيل النسيج",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="خيط الغزل",
        required=True,
        ondelete="restrict",
        help="صنف خيط الغزل بالمخزن (قطن، بوليستر، ليكرا، مخلوط)",
    )
    yarn_role = fields.Selection(
        [
            ("ground", "خيط أرضية / أساسي (Ground)"),
            ("lycra", "ليكرا / إيلاستين (Lycra)"),
            ("warp", "خيط سداء (Warp)"),
            ("weft", "خيط لحمة (Weft)"),
            ("pile", "خيط وبرة (Pile / Terry)"),
            ("inlay", "خيط حشو (Inlay)"),
        ],
        string="دور الخيط في القماش",
        default="ground",
        required=True,
    )
    yarn_count = fields.Char(
        string="نمرة الغزل",
        help="مثال: 30/1 مشط، 24/1 كارد، 40D دنير",
    )
    yarn_lot_id = fields.Many2one(
        "stock.lot",
        string="لوط الغزل (المخزن)",
        domain="[('product_id', '=', product_id)]",
        help="رقم لوط الغزل الخام المسحوب من المخزن للتتبع التام",
    )
    yarn_lot_name = fields.Char(
        string="رقم لوط الغزل",
        help="في حال عدم استخدام تتبع مخزني للغزل يمكن كتابة رقم لوط المورد مباشرة",
    )
    blend_percentage = fields.Float(
        string="نسبة الخلط (%)",
        digits=(5, 2),
        help="النسبة المئوية للخيط في تركيبة القماش (مثلاً: 95% قطن، 5% ليكرا)",
    )
    planned_qty_kg = fields.Float(
        string="الكمية المخططة (كجم)",
        digits=(16, 3),
        help="الوزن المخطط استهلاكه من هذا الغزل",
    )
    consumed_qty_kg = fields.Float(
        string="المستهلك الفعلي (كجم)",
        digits=(16, 3),
        help="الوزن الفعلي المنصرف والمستهلك من هذا الغزل",
    )
    unit_cost = fields.Monetary(
        string="سعر الكيلو",
        help="سعر شراء أو تكلفة كجم الغزل",
    )
    subtotal_cost = fields.Monetary(
        string="إجمالي التكلفة",
        compute="_compute_subtotal_cost",
        store=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="order_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="order_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_cost = self.product_id.standard_price

    @api.onchange("yarn_lot_id")
    def _onchange_yarn_lot_id(self):
        if self.yarn_lot_id:
            self.yarn_lot_name = self.yarn_lot_id.name

    @api.depends("consumed_qty_kg", "planned_qty_kg", "unit_cost")
    def _compute_subtotal_cost(self):
        for line in self:
            qty = line.consumed_qty_kg if line.consumed_qty_kg > 0 else line.planned_qty_kg
            line.subtotal_cost = qty * line.unit_cost

    @api.constrains("blend_percentage", "planned_qty_kg", "consumed_qty_kg", "unit_cost")
    def _check_positive_values(self):
        for line in self:
            if line.blend_percentage < 0 or line.blend_percentage > 100:
                raise ValidationError("نسبة الخلط يجب أن تكون بين 0 و 100%.")
            if any(v < 0 for v in [line.planned_qty_kg, line.consumed_qty_kg, line.unit_cost]):
                raise ValidationError("كميات وتكلفة خيوط الغزل لا يمكن أن تكون سالبة.")
