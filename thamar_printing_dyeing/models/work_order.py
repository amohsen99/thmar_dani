# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DyeingWorkOrder(models.Model):
    _name = "thamar.dyeing.work.order"
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
    # Technical compatibility field. It is intentionally absent from all views
    # and no business logic changes it while the module works in data-entry mode.
    state = fields.Selection(
        [
            ("draft", "إدخال بيانات"),
            ("confirmed", "إدخال بيانات"),
            ("progress", "إدخال بيانات"),
            ("done", "إدخال بيانات"),
            ("cancelled", "إدخال بيانات"),
        ],
        string="الحالة التقنية",
        required=True,
        default="draft",
        copy=False,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="كود العميل",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    message_number = fields.Char(string="رقم الرسالة", required=True, tracking=True)
    product_id = fields.Many2one(
        "product.product",
        string="اسم الخام",
        required=True,
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
    planned_weight_kg = fields.Float(
        string="الوزن المتوقع (كجم)", digits=(16, 3), tracking=True
    )
    planned_meter = fields.Float(
        string="الأمتار المتوقعة", digits=(16, 2), tracking=True
    )
    actual_weight_kg = fields.Float(
        string="الوزن الفعلي (كجم)",
        digits=(16, 3),
        tracking=True,
        copy=False,
    )
    actual_meter = fields.Float(
        string="الأمتار الفعلية",
        digits=(16, 2),
        tracking=True,
        copy=False,
    )
    actual_quantities_set = fields.Boolean(
        string="تم اعتماد الكميات الفعلية",
        tracking=True,
        copy=False,
    )
    operation_ids = fields.One2many(
        "thamar.dyeing.operation",
        "work_order_id",
        string="مراحل التشغيل",
        copy=True,
    )
    current_stage_id = fields.Many2one(
        "thamar.dyeing.stage.type",
        string="المرحلة الحالية",
        compute="_compute_totals",
        store=True,
    )
    operation_count = fields.Integer(
        string="عدد المراحل", compute="_compute_totals", store=True
    )
    total_actual_weight_kg = fields.Float(
        string="إجمالي الوزن المنفذ",
        compute="_compute_totals",
        store=True,
        digits=(16, 3),
    )
    total_cost = fields.Monetary(
        string="إجمالي تكلفة التشغيل", compute="_compute_totals", store=True
    )
    actual_start_time = fields.Datetime(
        string="أول وقت دخول", compute="_compute_totals", store=True
    )
    actual_end_time = fields.Datetime(
        string="آخر وقت خروج", compute="_compute_totals", store=True
    )
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
    notes = fields.Text(string="ملاحظات")

    @api.depends(
        "operation_ids",
        "operation_ids.sequence",
        "operation_ids.stage_type_id",
        "operation_ids.weight_kg",
        "operation_ids.total_cost",
        "operation_ids.entry_time",
        "operation_ids.exit_time",
    )
    def _compute_totals(self):
        for order in self:
            operations = order.operation_ids.sorted(lambda operation: (operation.sequence, operation.id))
            current = operations.filtered(lambda operation: not operation.exit_time)[:1]
            order.current_stage_id = current.stage_type_id if current else False
            order.operation_count = len(operations)
            order.total_actual_weight_kg = sum(
                operations.filtered("exit_time").mapped("weight_kg")
            )
            order.total_cost = sum(operations.mapped("total_cost"))
            entry_times = [
                operation.entry_time
                for operation in operations
                if operation.entry_time
            ]
            exit_times = [
                operation.exit_time
                for operation in operations
                if operation.exit_time
            ]
            order.actual_start_time = min(entry_times) if entry_times else False
            order.actual_end_time = max(exit_times) if exit_times else False

    @api.constrains(
        "planned_weight_kg", "planned_meter", "actual_weight_kg", "actual_meter"
    )
    def _check_planned_quantities(self):
        for order in self:
            if any(
                value < 0
                for value in (
                    order.planned_weight_kg,
                    order.planned_meter,
                    order.actual_weight_kg,
                    order.actual_meter,
                )
            ):
                raise ValidationError("الوزن والأمتار لا يمكن أن تكون سالبة.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "جديد") == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "thamar.dyeing.work.order"
                ) or "جديد"
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if "partner_id" in vals:
            self.mapped("operation_ids").with_context(
                sync_customer_from_plan=True
            ).write({"partner_id": vals["partner_id"]})
        return result

    def action_view_operations(self):
        self.ensure_one()
        action = self.env.ref(
            "thamar_printing_dyeing.action_dyeing_operation"
        ).read()[0]
        action["domain"] = [("work_order_id", "=", self.id)]
        action["context"] = {
            "default_work_order_id": self.id,
            "search_default_group_stage": 1,
        }
        return action
