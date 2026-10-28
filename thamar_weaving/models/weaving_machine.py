# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WeavingMachine(models.Model):
    _name = "thamar.weaving.machine"
    _description = "Weaving Machine (Circular and Rectangular)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "weaving_type, name, id"

    name = fields.Char(string="اسم الماكينة", required=True, tracking=True)
    code = fields.Char(string="كود الماكينة", tracking=True)
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
            ("available", "جاهزة / متاحة"),
            ("running", "قيد التشغيل"),
            ("maintenance", "تحت الصيانة"),
            ("stopped", "متوقفة / عطل"),
        ],
        string="حالة الماكينة",
        default="available",
        tracking=True,
        required=True,
    )
    hall_location = fields.Char(
        string="العنبر / الصالة",
        tracking=True,
        help="مثال: صالة النسيج الدائري 1، عنبر الأنوال رابير 2",
    )
    brand_model = fields.Char(
        string="الماركة والموديل",
        help="مثال: Mayer & Cie, Picanol, Toyota, Itema, Terrot",
    )
    manufacture_year = fields.Char(string="سنة الصنع")

    # ─── المواصفات الفنية للنسيج الدائري ─────────────────────────────────
    diameter_inch = fields.Float(
        string="القطر (بوصة)",
        digits=(16, 1),
        tracking=True,
        help="قطر سلندر الماكينة بالبوصة مثل: 30، 32، 34 بوصة",
    )
    gauge = fields.Char(
        string="الجيج (Gauge)",
        tracking=True,
        help="عدد الإبر في البوصة الواحدة مثل: 20GG, 24GG, 28GG, 32GG",
    )
    feeders_count = fields.Integer(
        string="عدد المغذيات (Feeders)",
        tracking=True,
        help="عدد مسارات/مغذيات الخيوط على الماكينة مثل: 72، 84، 96 مغذي",
    )
    rpm = fields.Float(
        string="السرعة (دورة/دقيقة RPM)",
        digits=(16, 1),
        help="سرعة دوران السلندر",
    )

    # ─── المواصفات الفنية للنسيج المستطيل / الأنوال ───────────────────────
    reed_width_cm = fields.Float(
        string="عرض المشط (سم)",
        digits=(16, 1),
        tracking=True,
        help="أقصى عرض للمشط/القماش بالماكينة مثل: 190، 220، 280، 340 سم",
    )
    loom_type = fields.Selection(
        [
            ("rapier", "أنوال رابير (سهمي / Rapier)"),
            ("airjet", "أنوال قذف هوائي (Air-Jet)"),
            ("waterjet", "أنوال قذف مائي (Water-Jet)"),
            ("jacquard", "أنوال جاكار (Jacquard)"),
            ("projectile", "أنوال مقذوف (Projectile)"),
        ],
        string="نوع النول / الحدف",
        tracking=True,
    )
    speed_ppm = fields.Float(
        string="السرعة (رمية/دقيقة PPM)",
        digits=(16, 1),
        help="عدد رميات اللحمة في الدقيقة (Picks Per Minute)",
    )
    shafts_count = fields.Integer(
        string="عدد الدرء / اللمات",
        help="أقصى عدد لإطارات الدرء المتاحة على النول",
    )

    # ─── عناصر التكلفة التشغيلية للساعة ────────────────────────────────
    electricity_cost_hour = fields.Monetary(
        string="تكلفة الكهرباء / ساعة",
        tracking=True,
    )
    labor_cost_hour = fields.Monetary(
        string="تكلفة العمالة / ساعة",
        tracking=True,
    )
    spare_parts_cost_hour = fields.Monetary(
        string="قطع الغيار والصيانة / ساعة",
        tracking=True,
    )
    other_cost_hour = fields.Monetary(
        string="تكاليف أخرى / ساعة",
        tracking=True,
    )
    hourly_cost = fields.Monetary(
        string="إجمالي تكلفة الساعة",
        compute="_compute_hourly_cost",
        store=True,
        tracking=True,
    )

    # ─── معدلات الإنتاج المعيارية ─────────────────────────────────────────
    standard_production_rate_kg = fields.Float(
        string="معدل الإنتاج المعياري (كجم/ساعة)",
        digits=(16, 2),
        help="الكمية القياسية المتوقع إنتاجها بالكيلو جرام في الساعة",
    )
    standard_production_rate_meter = fields.Float(
        string="معدل الإنتاج المعياري (متر/ساعة)",
        digits=(16, 2),
        help="الكمية القياسية المتوقع إنتاجها بالأمتار في الساعة",
    )

    # ─── العلاقات والإحصائيات ───────────────────────────────────────────
    order_ids = fields.One2many(
        "thamar.weaving.order",
        "machine_id",
        string="أوامر التشغيل",
    )
    order_count = fields.Integer(
        string="عدد الأوامر",
        compute="_compute_statistics",
        store=True,
    )
    roll_ids = fields.One2many(
        "thamar.weaving.roll",
        "machine_id",
        string="الأتواب المنتجة",
    )
    roll_count = fields.Integer(
        string="عدد الأتواب المنتجة",
        compute="_compute_statistics",
        store=True,
    )
    total_produced_weight_kg = fields.Float(
        string="إجمالي الوزن المنتج (كجم)",
        compute="_compute_statistics",
        store=True,
        digits=(16, 3),
    )
    stop_ids = fields.One2many(
        "thamar.weaving.machine.stop",
        "machine_id",
        string="سجل التوقفات والأعطال",
    )
    stop_count = fields.Integer(
        string="عدد التوقفات",
        compute="_compute_statistics",
        store=True,
    )
    total_stop_minutes = fields.Float(
        string="إجمالي دقائق التوقف",
        compute="_compute_statistics",
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
    active = fields.Boolean(default=True)
    notes = fields.Text(string="ملاحظات فنية")

    @api.depends(
        "electricity_cost_hour",
        "labor_cost_hour",
        "spare_parts_cost_hour",
        "other_cost_hour",
    )
    def _compute_hourly_cost(self):
        for machine in self:
            machine.hourly_cost = (
                machine.electricity_cost_hour
                + machine.labor_cost_hour
                + machine.spare_parts_cost_hour
                + machine.other_cost_hour
            )

    @api.depends("order_ids", "roll_ids.net_weight_kg", "stop_ids.duration_minutes")
    def _compute_statistics(self):
        for machine in self:
            machine.order_count = len(machine.order_ids)
            machine.roll_count = len(machine.roll_ids)
            machine.total_produced_weight_kg = sum(machine.roll_ids.mapped("net_weight_kg"))
            machine.stop_count = len(machine.stop_ids)
            machine.total_stop_minutes = sum(machine.stop_ids.mapped("duration_minutes"))

    @api.constrains(
        "electricity_cost_hour",
        "labor_cost_hour",
        "spare_parts_cost_hour",
        "other_cost_hour",
        "standard_production_rate_kg",
        "standard_production_rate_meter",
    )
    def _check_non_negative_values(self):
        for machine in self:
            vals = [
                machine.electricity_cost_hour,
                machine.labor_cost_hour,
                machine.spare_parts_cost_hour,
                machine.other_cost_hour,
                machine.standard_production_rate_kg,
                machine.standard_production_rate_meter,
            ]
            if any(v < 0 for v in vals):
                raise ValidationError("تكاليف ومعدلات إنتاج الماكينة لا يمكن أن تكون سالبة.")

    def action_view_orders(self):
        self.ensure_one()
        return {
            "name": f"أوامر تشغيل الماكينة: {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "thamar.weaving.order",
            "view_mode": "list,form",
            "domain": [("machine_id", "=", self.id)],
            "context": {"default_machine_id": self.id, "default_weaving_type": self.weaving_type},
        }

    def action_view_rolls(self):
        self.ensure_one()
        return {
            "name": f"أتواب ولوطات الماكينة: {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "thamar.weaving.roll",
            "view_mode": "list,form",
            "domain": [("machine_id", "=", self.id)],
        }

    def action_view_stops(self):
        self.ensure_one()
        return {
            "name": f"توقفات وأعطال الماكينة: {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "thamar.weaving.machine.stop",
            "view_mode": "list,form",
            "domain": [("machine_id", "=", self.id)],
            "context": {"default_machine_id": self.id},
        }

    def action_set_available(self):
        self.write({"state": "available"})

    def action_set_maintenance(self):
        self.write({"state": "maintenance"})
