# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DyeingPlan(models.Model):
    _name = "thamar.dyeing.plan"
    _description = "Printing and Dyeing Production Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="رقم الخطة",
        required=True,
        copy=False,
        readonly=True,
        default="جديد",
        tracking=True,
    )
    date = fields.Date(
        string="تاريخ الخطة",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="العميل",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    message_number = fields.Char(string="رقم الرسالة", tracking=True)
    raw_product_id = fields.Many2one(
        "product.product",
        string="القماش الخام",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    finished_product_id = fields.Many2one(
        "product.product",
        string="المنتج التام (درجة أولى)",
        ondelete="restrict",
        tracking=True,
    )
    finished_product_grade2_id = fields.Many2one(
        "product.product",
        string="المنتج التام (درجة ثانية)",
        ondelete="restrict",
        tracking=True,
    )
    scrap_product_id = fields.Many2one(
        "product.product",
        string="صنف الهالك / الفضلات",
        ondelete="restrict",
        tracking=True,
    )
    color_id = fields.Many2one(
        "thamar.dyeing.color", string="اللون", ondelete="restrict", tracking=True
    )
    design_id = fields.Many2one(
        "thamar.dyeing.design", string="رقم الرسمة", ondelete="restrict", tracking=True
    )
    printing_type_id = fields.Many2one(
        "thamar.printing.type", string="نوع الطباعة", ondelete="restrict", tracking=True
    )
    dyeing_type_id = fields.Many2one(
        "thamar.dyeing.type", string="نوع الصباغة", ondelete="restrict", tracking=True
    )
    machine_id = fields.Many2one(
        "thamar.dyeing.machine",
        string="الماكينة المستهدفة",
        ondelete="restrict",
        tracking=True,
    )
    batch_capacity_kg = fields.Float(
        string="سعة التشغيلة (كجم)",
        digits=(16, 3),
        help="سعة الماكينة للتشغيلة الواحدة؛ تُستخدم لتجزئة الخطة إلى أوامر تشغيل.",
        tracking=True,
    )
    planned_weight_kg = fields.Float(
        string="إجمالي الوزن المخطط (كجم)", digits=(16, 3), required=True, tracking=True
    )
    planned_meter = fields.Float(
        string="إجمالي الأمتار المخططة", digits=(16, 2), tracking=True
    )
    work_order_ids = fields.One2many(
        "thamar.dyeing.work.order",
        "plan_id",
        string="أوامر التشغيل الناتجة",
    )
    work_order_count = fields.Integer(
        string="عدد أوامر التشغيل", compute="_compute_totals", store=True
    )
    total_actual_weight_kg = fields.Float(
        string="إجمالي الوزن المنفذ (كجم)",
        compute="_compute_totals",
        store=True,
        digits=(16, 3),
    )
    total_grade1_weight_kg = fields.Float(
        string="إجمالي وزن درجة 1 (كجم)",
        compute="_compute_totals",
        store=True,
        digits=(16, 3),
    )
    total_grade2_weight_kg = fields.Float(
        string="إجمالي وزن درجة 2 (كجم)",
        compute="_compute_totals",
        store=True,
        digits=(16, 3),
    )
    total_scrap_weight_kg = fields.Float(
        string="إجمالي وزن الهالك (كجم)",
        compute="_compute_totals",
        store=True,
        digits=(16, 3),
    )
    total_rolls_count = fields.Integer(
        string="إجمالي الأتواب المنتجة",
        compute="_compute_totals",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("confirmed", "مؤكدة"),
            ("progress", "قيد التشغيل"),
            ("done", "منتهية"),
            ("cancelled", "ملغاة"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="الشركة",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    notes = fields.Text(string="ملاحظات")

    @api.onchange("machine_id")
    def _onchange_machine_id(self):
        if self.machine_id and self.machine_id.capacity_kg:
            self.batch_capacity_kg = self.machine_id.capacity_kg

    @api.depends(
        "work_order_ids",
        "work_order_ids.total_output_weight_kg",
        "work_order_ids.actual_weight_kg",
        "work_order_ids.grade1_weight_kg",
        "work_order_ids.grade2_weight_kg",
        "work_order_ids.scrap_weight_kg",
        "work_order_ids.total_rolls_count",
    )
    def _compute_totals(self):
        for plan in self:
            orders = plan.work_order_ids
            plan.work_order_count = len(orders)
            plan.total_actual_weight_kg = sum(
                orders.mapped("total_output_weight_kg")
            ) or sum(orders.mapped("actual_weight_kg"))
            plan.total_grade1_weight_kg = sum(orders.mapped("grade1_weight_kg"))
            plan.total_grade2_weight_kg = sum(orders.mapped("grade2_weight_kg"))
            plan.total_scrap_weight_kg = sum(orders.mapped("scrap_weight_kg"))
            plan.total_rolls_count = sum(orders.mapped("total_rolls_count"))

    @api.constrains("planned_weight_kg", "planned_meter", "batch_capacity_kg")
    def _check_quantities(self):
        for plan in self:
            if plan.planned_weight_kg < 0 or plan.planned_meter < 0 or plan.batch_capacity_kg < 0:
                raise ValidationError("الكميات المخططة وسعة التشغيلة لا يمكن أن تكون سالبة.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "جديد") == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "thamar.dyeing.plan"
                ) or "جديد"
        return super().create(vals_list)

    def action_confirm(self):
        for plan in self:
            if plan.planned_weight_kg <= 0:
                raise ValidationError("يرجى إدخال وزن مخطط أكبر من الصفر.")
            plan.state = "confirmed"

    def action_draft(self):
        self.write({"state": "draft"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_generate_work_orders(self):
        self.ensure_one()
        if self.planned_weight_kg <= 0:
            raise ValidationError("يرجى إدخال وزن مخطط أكبر من الصفر قبل التجزئة.")

        capacity = self.batch_capacity_kg or (
            self.machine_id.capacity_kg if self.machine_id else 0.0
        )
        if capacity <= 0 or capacity >= self.planned_weight_kg:
            batch_weights = [self.planned_weight_kg]
        else:
            batch_weights = []
            remaining = self.planned_weight_kg
            while remaining > 0:
                current_weight = min(remaining, capacity)
                batch_weights.append(round(current_weight, 3))
                remaining = round(remaining - current_weight, 3)

        total_meter = self.planned_meter or 0.0
        work_order_vals = []
        for index, weight in enumerate(batch_weights, start=1):
            meter_share = (
                round((weight / self.planned_weight_kg) * total_meter, 2)
                if total_meter
                else 0.0
            )
            lot_name = (
                f"{self.message_number}-{index}"
                if self.message_number
                else f"{self.name}-{index}"
            )
            vals = {
                "plan_id": self.id,
                "partner_id": self.partner_id.id,
                "message_number": lot_name,
                "product_id": self.raw_product_id.id,
                "finished_product_id": self.finished_product_id.id
                if self.finished_product_id
                else False,
                "finished_product_grade2_id": self.finished_product_grade2_id.id
                if self.finished_product_grade2_id
                else False,
                "scrap_product_id": self.scrap_product_id.id
                if self.scrap_product_id
                else False,
                "color_id": self.color_id.id if self.color_id else False,
                "design_id": self.design_id.id if self.design_id else False,
                "printing_type_id": self.printing_type_id.id
                if self.printing_type_id
                else False,
                "dyeing_type_id": self.dyeing_type_id.id
                if self.dyeing_type_id
                else False,
                "planned_weight_kg": weight,
                "planned_meter": meter_share,
                "date": self.date,
                "company_id": self.company_id.id,
            }
            work_order_vals.append(vals)

        created_orders = self.env["thamar.dyeing.work.order"].create(work_order_vals)
        self.write({"state": "progress"})
        self.message_post(
            body=_(
                "تم إنشاء %(count)s أمر تشغيل بناءً على طاقة الماكينة (%(capacity)s كجم).",
                count=len(created_orders),
                capacity=capacity or self.planned_weight_kg,
            )
        )
        return self.action_view_work_orders()

    def action_view_work_orders(self):
        self.ensure_one()
        action = self.env.ref(
            "thamar_printing_dyeing.action_dyeing_work_order"
        ).read()[0]
        action["domain"] = [("plan_id", "=", self.id)]
        action["context"] = {
            "default_plan_id": self.id,
            "default_partner_id": self.partner_id.id,
            "default_product_id": self.raw_product_id.id,
            "default_finished_product_id": self.finished_product_id.id
            if self.finished_product_id
            else False,
            "default_finished_product_grade2_id": self.finished_product_grade2_id.id
            if self.finished_product_grade2_id
            else False,
            "default_scrap_product_id": self.scrap_product_id.id
            if self.scrap_product_id
            else False,
            "default_color_id": self.color_id.id if self.color_id else False,
            "default_design_id": self.design_id.id if self.design_id else False,
            "default_printing_type_id": self.printing_type_id.id
            if self.printing_type_id
            else False,
            "default_dyeing_type_id": self.dyeing_type_id.id
            if self.dyeing_type_id
            else False,
        }
        return action
