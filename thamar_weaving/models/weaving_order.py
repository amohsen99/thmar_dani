# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class WeavingOrder(models.Model):
    _name = "thamar.weaving.order"
    _description = "Weaving Production Order (Circular and Rectangular)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "order_date desc, id desc"

    name = fields.Char(
        string="رقم أمر التشغيل",
        required=True,
        copy=False,
        readonly=True,
        default="جديد",
        tracking=True,
    )
    order_date = fields.Date(
        string="تاريخ الأمر",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    weaving_type = fields.Selection(
        [
            ("circular", "نسيج دائري (Circular Knitting)"),
            ("rectangular", "نسيج مستطيل / مسطح (Looms Weaving)"),
        ],
        string="نوع النسيج",
        required=True,
        default="circular",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("confirmed", "مؤكد / جاهز"),
            ("in_progress", "قيد التشغيل"),
            ("done", "تم الإنتاج والتسليم"),
            ("cancel", "ملغي"),
        ],
        string="الحالة",
        default="draft",
        tracking=True,
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="العميل",
        ondelete="restrict",
        tracking=True,
        help="العميل في حالة التشغيل للغير، أو يمكن تركه فارغاً للإنتاج الداخلي",
    )
    is_internal = fields.Boolean(
        string="إنتاج داخلي لمخزن المصنع",
        default=True,
        tracking=True,
    )
    machine_id = fields.Many2one(
        "thamar.weaving.machine",
        string="الماكينة",
        required=True,
        ondelete="restrict",
        domain="[('weaving_type', '=', weaving_type), ('company_id', '=', company_id)]",
        tracking=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="صنف القماش الخام",
        required=True,
        ondelete="restrict",
        tracking=True,
        help="صنف القماش المنتج (مثل: سنجل جيرسي 100% قطن، بوبلين منسوج، إلخ)",
    )

    # ─── المواصفات والكميات المخططة ─────────────────────────────────────
    planned_weight_kg = fields.Float(
        string="الوزن المخطط (كجم)",
        digits=(16, 3),
        required=True,
        tracking=True,
    )
    planned_meter = fields.Float(
        string="الأمتار المخططة",
        digits=(16, 2),
        tracking=True,
    )
    target_gsm = fields.Float(
        string="الوزن المستهدف (GSM)",
        digits=(16, 1),
        tracking=True,
        help="وزن المتر المربع المخطط بالجرام (g/m²)",
    )
    target_width_cm = fields.Float(
        string="العرض المستهدف (سم)",
        digits=(16, 1),
        tracking=True,
    )

    # ─── مواصفات خاصة بالنسيج الدائري ────────────────────────────────────
    stitch_length_mm = fields.Float(
        string="طول الغرزة (مم)",
        digits=(16, 2),
        tracking=True,
        help="طول الغرزة (Stitch / Loop Length) بالمليمتر",
    )
    lycra_percentage = fields.Float(
        string="نسبة الليكرا (%)",
        digits=(5, 2),
        tracking=True,
    )

    # ─── مواصفات خاصة بالنسيج المستطيل / الأنوال ─────────────────────────
    warp_density = fields.Float(
        string="كثافة السداء (خيط/سم)",
        digits=(16, 1),
        tracking=True,
        help="عدد خيوط السداء في السنتيمتر (Warp Ends / cm)",
    )
    weft_density = fields.Float(
        string="كثافة اللحمة (حدفة/سم)",
        digits=(16, 1),
        tracking=True,
        help="عدد حدفات اللحمة في السنتيمتر (Weft Picks / cm)",
    )
    reed_number = fields.Char(
        string="نمرة المشط (Reed No)",
        tracking=True,
    )
    reed_width_used_cm = fields.Float(
        string="عرض المشط المشغول (سم)",
        digits=(16, 1),
        tracking=True,
    )
    weave_pattern = fields.Char(
        string="التركيب النسجي",
        tracking=True,
        help="سادة 1/1، مبرد 2/1، أطلس 5/2، إلخ",
    )

    # ─── بيانات التنفيذ والوردية ─────────────────────────────────────────
    start_time = fields.Datetime(string="وقت البدء الفعلي", tracking=True)
    end_time = fields.Datetime(string="وقت الانتهاء الفعلي", tracking=True)
    operating_hours = fields.Float(
        string="ساعات التشغيل الفعلية",
        compute="_compute_operating_hours",
        store=True,
        readonly=False,
        digits=(16, 2),
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
    supervisor_id = fields.Many2one(
        "res.users",
        string="رئيس الوردية / المشرف",
        default=lambda self: self.env.user,
        tracking=True,
    )
    operator_name = fields.Char(string="فني / نساج الماكينة", tracking=True)

    # ─── جدول خيوط الغزل المستهلكة ───────────────────────────────────────
    yarn_line_ids = fields.One2many(
        "thamar.weaving.yarn.line",
        "order_id",
        string="خيوط الغزل واللوطات",
    )
    total_yarn_planned_kg = fields.Float(
        string="إجمالي الغزل المخطط (كجم)",
        compute="_compute_yarn_totals",
        store=True,
        digits=(16, 3),
    )
    total_yarn_consumed_kg = fields.Float(
        string="إجمالي الغزل المستهلك (كجم)",
        compute="_compute_yarn_totals",
        store=True,
        digits=(16, 3),
    )
    total_yarn_cost = fields.Monetary(
        string="إجمالي تكلفة الغزل",
        compute="_compute_yarn_totals",
        store=True,
    )

    # ─── سجل الأتواب والتتبع باللوط ─────────────────────────────────────
    roll_ids = fields.One2many(
        "thamar.weaving.roll",
        "order_id",
        string="الأتواب واللوطات المنتجة",
    )
    roll_count = fields.Integer(
        string="عدد الأتواب",
        compute="_compute_roll_totals",
        store=True,
    )
    total_gross_weight_kg = fields.Float(
        string="إجمالي الوزن القائم (كجم)",
        compute="_compute_roll_totals",
        store=True,
        digits=(16, 3),
    )
    total_tare_weight_kg = fields.Float(
        string="إجمالي وزن الفوارغ (كجم)",
        compute="_compute_roll_totals",
        store=True,
        digits=(16, 3),
    )
    total_net_weight_kg = fields.Float(
        string="إجمالي الوزن الصافي المنتج (كجم)",
        compute="_compute_roll_totals",
        store=True,
        digits=(16, 3),
    )
    total_meter = fields.Float(
        string="إجمالي الأمتار الفعلية",
        compute="_compute_roll_totals",
        store=True,
        digits=(16, 2),
    )
    avg_roll_weight_kg = fields.Float(
        string="متوسط وزن الثوب (كجم)",
        compute="_compute_roll_totals",
        store=True,
        digits=(16, 2),
    )

    # ─── تصنيف الجودة ومؤشرات الهالك (KPIs) ──────────────────────────────
    grade_a_rolls_count = fields.Integer(
        string="أتواب درجة أولى",
        compute="_compute_roll_totals",
        store=True,
    )
    grade_a_weight_kg = fields.Float(
        string="وزن درجة أولى (كجم)",
        compute="_compute_roll_totals",
        store=True,
        digits=(16, 3),
    )
    grade_b_rolls_count = fields.Integer(
        string="أتواب درجة ثانية",
        compute="_compute_roll_totals",
        store=True,
    )
    grade_b_weight_kg = fields.Float(
        string="وزن درجة ثانية (كجم)",
        compute="_compute_roll_totals",
        store=True,
        digits=(16, 3),
    )
    scrap_rolls_count = fields.Integer(
        string="أتواب هالك / فضلات",
        compute="_compute_roll_totals",
        store=True,
    )
    scrap_weight_kg = fields.Float(
        string="وزن هالك الأتواب (كجم)",
        compute="_compute_roll_totals",
        store=True,
        digits=(16, 3),
    )
    waste_weight_kg = fields.Float(
        string="إجمالي هالك التشغيل (كجم)",
        compute="_compute_waste_and_costs",
        store=True,
        digits=(16, 3),
        help="الفرق بين الغزل المستهلك والوزن الصافي للقماش المنتج",
    )
    waste_percentage = fields.Float(
        string="نسبة الهالك (%)",
        compute="_compute_waste_and_costs",
        store=True,
        digits=(16, 2),
    )

    # ─── التكاليف ومحاسبة التشغيل ───────────────────────────────────────
    machine_hourly_cost = fields.Monetary(
        string="قيمة ساعة الماكينة",
        related="machine_id.hourly_cost",
        store=True,
        readonly=True,
    )
    machine_operating_cost = fields.Monetary(
        string="تكلفة تشغيل الماكينة",
        compute="_compute_waste_and_costs",
        store=True,
    )
    total_production_cost = fields.Monetary(
        string="إجمالي تكلفة أمر التشغيل",
        compute="_compute_waste_and_costs",
        store=True,
    )
    cost_per_kg = fields.Monetary(
        string="تكلفة الكيلو جرام الصافي",
        compute="_compute_waste_and_costs",
        store=True,
    )

    # ─── الإعدادات العامة ────────────────────────────────────────────────
    company_id = fields.Many2one(
        "res.company",
        string="الشركة",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    notes = fields.Text(string="ملاحظات وتوجيهات التشغيل")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "جديد") == "جديد":
                seq_code = "thamar.weaving.order.circular" if vals.get("weaving_type") == "circular" else "thamar.weaving.order.rectangular"
                vals["name"] = self.env["ir.sequence"].next_by_code(seq_code) or self.env["ir.sequence"].next_by_code("thamar.weaving.order") or "WO-WEAV"
        return super().create(vals_list)

    @api.onchange("weaving_type")
    def _onchange_weaving_type(self):
        if self.machine_id and self.machine_id.weaving_type != self.weaving_type:
            self.machine_id = False

    @api.depends("start_time", "end_time")
    def _compute_operating_hours(self):
        for order in self:
            if order.start_time and order.end_time:
                diff = (order.end_time - order.start_time).total_seconds() / 3600.0
                order.operating_hours = max(round(diff, 2), 0.0)

    @api.depends("yarn_line_ids.planned_qty_kg", "yarn_line_ids.consumed_qty_kg", "yarn_line_ids.subtotal_cost")
    def _compute_yarn_totals(self):
        for order in self:
            order.total_yarn_planned_kg = sum(order.yarn_line_ids.mapped("planned_qty_kg"))
            order.total_yarn_consumed_kg = sum(order.yarn_line_ids.mapped("consumed_qty_kg"))
            order.total_yarn_cost = sum(order.yarn_line_ids.mapped("subtotal_cost"))

    @api.depends("roll_ids.gross_weight_kg", "roll_ids.tare_weight_kg", "roll_ids.net_weight_kg", "roll_ids.length_meter", "roll_ids.grade")
    def _compute_roll_totals(self):
        for order in self:
            rolls = order.roll_ids
            order.roll_count = len(rolls)
            order.total_gross_weight_kg = sum(rolls.mapped("gross_weight_kg"))
            order.total_tare_weight_kg = sum(rolls.mapped("tare_weight_kg"))
            order.total_net_weight_kg = sum(rolls.mapped("net_weight_kg"))
            order.total_meter = sum(rolls.mapped("length_meter"))
            order.avg_roll_weight_kg = (order.total_net_weight_kg / order.roll_count) if order.roll_count > 0 else 0.0

            grade_a = rolls.filtered(lambda r: r.grade == "grade_a")
            grade_b = rolls.filtered(lambda r: r.grade == "grade_b")
            scrap = rolls.filtered(lambda r: r.grade == "scrap")

            order.grade_a_rolls_count = len(grade_a)
            order.grade_a_weight_kg = sum(grade_a.mapped("net_weight_kg"))
            order.grade_b_rolls_count = len(grade_b)
            order.grade_b_weight_kg = sum(grade_b.mapped("net_weight_kg"))
            order.scrap_rolls_count = len(scrap)
            order.scrap_weight_kg = sum(scrap.mapped("net_weight_kg"))

    @api.depends(
        "total_yarn_consumed_kg",
        "total_net_weight_kg",
        "total_yarn_cost",
        "operating_hours",
        "machine_hourly_cost",
    )
    def _compute_waste_and_costs(self):
        for order in self:
            yarn_qty = order.total_yarn_consumed_kg
            net_fabric = order.total_net_weight_kg
            if yarn_qty > 0 and net_fabric > 0:
                waste = yarn_qty - net_fabric
                order.waste_weight_kg = max(round(waste, 3), 0.0)
                order.waste_percentage = round((order.waste_weight_kg / yarn_qty) * 100.0, 2)
            else:
                order.waste_weight_kg = 0.0
                order.waste_percentage = 0.0

            order.machine_operating_cost = (order.operating_hours or 0.0) * (order.machine_hourly_cost or 0.0)
            order.total_production_cost = (order.total_yarn_cost or 0.0) + order.machine_operating_cost
            if order.total_net_weight_kg > 0:
                order.cost_per_kg = order.total_production_cost / order.total_net_weight_kg
            else:
                order.cost_per_kg = 0.0

    # ─── أزرار التحكم وحالات التشغيل ─────────────────────────────────────
    def action_confirm(self):
        for order in self:
            if not order.yarn_line_ids:
                raise UserError("يرجى إضافة خيوط الغزل المطلوبة قبل تأكيد أمر التشغيل.")
            order.write({"state": "confirmed"})

    def action_start(self):
        for order in self:
            vals = {"state": "in_progress"}
            if not order.start_time:
                vals["start_time"] = fields.Datetime.now()
            order.write(vals)
            if order.machine_id:
                order.machine_id.write({"state": "running"})

    def action_done(self):
        for order in self:
            if not order.roll_ids:
                raise UserError("لا يمكن إنهاء أمر التشغيل بدون تسجيل ثوب واحد على الأقل.")
            vals = {"state": "done"}
            if not order.end_time:
                vals["end_time"] = fields.Datetime.now()
            order.write(vals)
            if order.machine_id and order.machine_id.state == "running":
                order.machine_id.write({"state": "available"})

    def action_cancel(self):
        for order in self:
            order.write({"state": "cancel"})
            if order.machine_id and order.machine_id.state == "running":
                order.machine_id.write({"state": "available"})

    def action_draft(self):
        for order in self:
            order.write({"state": "draft"})

    def action_quick_add_roll(self):
        """تنزيل ثوب جديد على الماكينة مع توليد رقم اللوط تلقائيًا"""
        self.ensure_one()
        roll_index = len(self.roll_ids) + 1
        lot_code = f"LOT-{self.name}-{roll_index:02d}"
        roll = self.env["thamar.weaving.roll"].create({
            "order_id": self.id,
            "lot_name": lot_code,
            "tare_weight_kg": 0.5,
            "gross_weight_kg": 25.5,  # وزن افتراضي للتعديل السريع
            "shift": self.shift,
            "operator_name": self.operator_name,
            "measured_gsm": self.target_gsm,
            "measured_width_cm": self.target_width_cm,
        })
        return {
            "name": f"ثوب جديد: {roll.name}",
            "type": "ir.actions.act_window",
            "res_model": "thamar.weaving.roll",
            "res_id": roll.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_rolls(self):
        self.ensure_one()
        return {
            "name": f"أتواب أمر التشغيل {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "thamar.weaving.roll",
            "view_mode": "list,form",
            "domain": [("order_id", "=", self.id)],
            "context": {"default_order_id": self.id},
        }
