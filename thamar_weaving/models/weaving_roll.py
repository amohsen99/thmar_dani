# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class WeavingRoll(models.Model):
    _name = "thamar.weaving.roll"
    _description = "Weaving Greige Fabric Roll & Lot Tracking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="رقم الثوب",
        required=True,
        copy=False,
        readonly=True,
        default="جديد",
        tracking=True,
    )
    lot_name = fields.Char(
        string="رقم اللوط",
        required=True,
        copy=False,
        tracking=True,
        help="الرقم التعريفي الفريد للوت القماش الخام الذي يتم تسليمه للمخزن والمصبغة",
    )
    lot_id = fields.Many2one(
        "stock.lot",
        string="لوط المخزون المعتمد",
        readonly=True,
        index=True,
        copy=False,
        help="سجل اللوط المنشأ تلقائيًا في المخازن لهذا الثوب",
    )
    order_id = fields.Many2one(
        "thamar.weaving.order",
        string="أمر تشغيل النسيج",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    weaving_type = fields.Selection(
        related="order_id.weaving_type",
        string="نوع النسيج",
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product",
        related="order_id.product_id",
        string="صنف القماش الخام",
        store=True,
        readonly=True,
    )
    machine_id = fields.Many2one(
        "thamar.weaving.machine",
        related="order_id.machine_id",
        string="ماكينة النسيج",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        related="order_id.partner_id",
        string="العميل",
        store=True,
        readonly=True,
    )
    date = fields.Datetime(
        string="تاريخ ووقت النزول",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    shift = fields.Selection(
        [
            ("shift1", "الوردية الأولى (صباحية)"),
            ("shift2", "الوردية الثانية (مسائية)"),
            ("shift3", "الوردية الثالثة (ليلية)"),
        ],
        string="الوردية",
        default="shift1",
        tracking=True,
    )
    operator_name = fields.Char(string="فني / نساج الماكينة", tracking=True)

    # ─── الأوزان والمقاسات ───────────────────────────────────────────────
    gross_weight_kg = fields.Float(
        string="الوزن القائم (كجم)",
        digits=(16, 3),
        required=True,
        tracking=True,
        help="الوزن الإجمالي للثوب شامل ماسورة الكرتون",
    )
    tare_weight_kg = fields.Float(
        string="وزن الفارغ / الماسورة (كجم)",
        digits=(16, 3),
        default=0.5,
        required=True,
        help="وزن الماسورة الكرتون أو البلاستيك",
    )
    net_weight_kg = fields.Float(
        string="الوزن الصافي (كجم)",
        compute="_compute_net_weight",
        store=True,
        digits=(16, 3),
        tracking=True,
    )
    length_meter = fields.Float(
        string="الطول الفعلي (متر)",
        digits=(16, 2),
        tracking=True,
    )
    measured_gsm = fields.Float(
        string="وزن المتر المربع الفعلي (GSM)",
        digits=(16, 1),
        tracking=True,
        help="الوزن المقاس للمتر المربع بالجرام",
    )
    measured_width_cm = fields.Float(
        string="العرض الفعلي المقاس (سم)",
        digits=(16, 1),
        tracking=True,
    )

    # ─── فحص الجودة والتصنيف ────────────────────────────────────────────
    grade = fields.Selection(
        [
            ("grade_a", "درجة أولى (ممتاز)"),
            ("grade_b", "درجة ثانية"),
            ("scrap", "هالك / فضلات"),
        ],
        string="درجة الجودة",
        default="grade_a",
        required=True,
        tracking=True,
    )
    defect_type = fields.Selection(
        [
            ("none", "بدون عيوب"),
            ("drop_stitch", "تسقيط إبرة / غرزة"),
            ("hole", "ثقب / قطع"),
            ("oil_stain", "بقع زيت"),
            ("yarn_fault", "عقدة / وصلة خيط"),
            ("uneven_density", "اختلاف كثافة / خطوط سداء أو لحمة"),
            ("other", "أخرى"),
        ],
        string="نوع العيب",
        default="none",
    )
    defect_notes = fields.Text(string="ملاحظات فحص الجودة")

    # ─── حالة الثوب والتكامل مع المخزن والمصبغة ──────────────────────────
    state = fields.Selection(
        [
            ("draft", "مسودة / تحت النزول"),
            ("inspected", "تم الفحص والجودة"),
            ("stock", "تم توريد المخزن"),
            ("delivered_dyeing", "تم التحويل للطباعة والصباغة"),
        ],
        string="حالة الثوب",
        default="draft",
        tracking=True,
    )
    barcode = fields.Char(string="باركود الثوب", copy=False)
    dyeing_work_order_id = fields.Many2one(
        "thamar.dyeing.work.order",
        string="أمر تشغيل الصباغة المرتبط",
        readonly=True,
        copy=False,
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "جديد") == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code("thamar.weaving.roll") or "ROLL"
            if not vals.get("lot_name"):
                order = self.env["thamar.weaving.order"].browse(vals.get("order_id"))
                roll_index = len(order.roll_ids) + 1 if order else 1
                order_ref = order.name if order else "WV"
                vals["lot_name"] = f"LOT-{order_ref}-{roll_index:02d}"
            if not vals.get("barcode"):
                vals["barcode"] = vals["lot_name"]
        rolls = super().create(vals_list)
        for roll in rolls:
            roll._sync_stock_lot()
        return rolls

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ["lot_name", "gross_weight_kg", "tare_weight_kg", "length_meter", "measured_gsm", "measured_width_cm", "grade"]):
            for roll in self:
                roll._sync_stock_lot()
        return res

    @api.depends("gross_weight_kg", "tare_weight_kg")
    def _compute_net_weight(self):
        for roll in self:
            roll.net_weight_kg = max(round(roll.gross_weight_kg - roll.tare_weight_kg, 3), 0.0)

    @api.constrains("gross_weight_kg", "tare_weight_kg")
    def _check_weights(self):
        for roll in self:
            if roll.gross_weight_kg < 0 or roll.tare_weight_kg < 0:
                raise ValidationError("الأوزان لا يمكن أن تكون سالبة.")
            if roll.gross_weight_kg < roll.tare_weight_kg:
                raise ValidationError("الوزن القائم لا يمكن أن يكون أقل من وزن الفارغ.")

    def _sync_stock_lot(self):
        """إنشاء أو تحديث لوط المخزون stock.lot المرتبط بهذا الثوب مع الخصائص الفنية"""
        for roll in self:
            if not roll.product_id or not roll.lot_name:
                continue

            # تجميع ملخص خيوط الغزل المستخدمة في أمر التشغيل
            yarn_summary_parts = []
            for y_line in roll.order_id.yarn_line_ids:
                part = f"{y_line.product_id.name}"
                if y_line.yarn_count:
                    part += f" ({y_line.yarn_count})"
                if y_line.yarn_lot_name:
                    part += f" لوط:{y_line.yarn_lot_name}"
                yarn_summary_parts.append(part)
            yarn_summary = " + ".join(yarn_summary_parts) if yarn_summary_parts else ""

            lot_vals = {
                "name": roll.lot_name,
                "product_id": roll.product_id.id,
                "company_id": roll.company_id.id,
                "weaving_order_id": roll.order_id.id,
                "weaving_roll_id": roll.id,
                "weaving_machine_id": roll.machine_id.id if roll.machine_id else False,
                "weaving_type": roll.weaving_type,
                "fabric_grade": roll.grade,
                "net_weight_kg": roll.net_weight_kg,
                "length_meter": roll.length_meter,
                "fabric_gsm": roll.measured_gsm,
                "fabric_width_cm": roll.measured_width_cm,
                "yarn_lot_summary": yarn_summary,
            }

            if roll.lot_id:
                roll.lot_id.sudo().write(lot_vals)
            else:
                existing_lot = self.env["stock.lot"].sudo().search(
                    [
                        ("name", "=", roll.lot_name),
                        ("product_id", "=", roll.product_id.id),
                        ("company_id", "=", roll.company_id.id),
                    ],
                    limit=1,
                )
                if existing_lot:
                    existing_lot.write(lot_vals)
                    roll.lot_id = existing_lot.id
                else:
                    new_lot = self.env["stock.lot"].sudo().create(lot_vals)
                    roll.lot_id = new_lot.id

    def action_inspect(self):
        self.ensure_one()
        self._sync_stock_lot()
        self.write({"state": "inspected"})

    def action_create_dyeing_work_order(self):
        """تحويل اللوط مباشرة إلى موديول الطباعة والصباغة وإنشاء أمر تشغيل صباغة"""
        self.ensure_one()
        if not self.lot_id:
            self._sync_stock_lot()

        dyeing_model = self.env["thamar.dyeing.work.order"]
        vals = {
            "partner_id": self.partner_id.id if self.partner_id else self.env.company.partner_id.id,
            "product_id": self.product_id.id,
            "message_number": self.lot_name,  # رقم اللوط يتم وضعه كرقم الرسالة / اللوط
            "planned_weight_kg": self.net_weight_kg,
            "planned_meter": self.length_meter,
            "rolls_count": 1,
            "notes": f"تم التحويل آليًا من موديول النسيج:\n"
                     f"- رقم الثوب: {self.name}\n"
                     f"- الماكينة: {self.machine_id.name if self.machine_id else ''}\n"
                     f"- النوع: {'نسيج دائري' if self.weaving_type == 'circular' else 'نسيج مستطيل'}\n"
                     f"- درجة الجودة: {dict(self._fields['grade'].selection).get(self.grade)}\n"
                     f"- الجراماج المقاس: {self.measured_gsm} GSM\n"
                     f"- العرض المقاس: {self.measured_width_cm} سم",
        }
        dyeing_order = dyeing_model.create(vals)
        self.write({
            "dyeing_work_order_id": dyeing_order.id,
            "state": "delivered_dyeing",
        })
        return {
            "name": f"أمر تشغيل الصباغة: {dyeing_order.name}",
            "type": "ir.actions.act_window",
            "res_model": "thamar.dyeing.work.order",
            "res_id": dyeing_order.id,
            "view_mode": "form",
        }
