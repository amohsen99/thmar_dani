# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DyeingBatch(models.Model):
    _name = "thamar.dyeing.batch"
    _description = "Multi-plan Machine Batch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "operation_date desc, id desc"

    name = fields.Char(
        string="رقم التشغيلة",
        required=True,
        readonly=True,
        copy=False,
        default="جديد",
        tracking=True,
    )
    stage_type_id = fields.Many2one(
        "thamar.dyeing.stage.type",
        string="المرحلة",
        required=True,
        ondelete="restrict",
        domain="[('allow_batching', '=', True)]",
        tracking=True,
    )
    machine_id = fields.Many2one(
        "thamar.dyeing.machine",
        string="الماكينة",
        required=True,
        ondelete="restrict",
        domain="[('stage_type_ids', 'in', [stage_type_id]), ('company_id', '=', company_id)]",
        tracking=True,
    )
    operation_ids = fields.Many2many(
        "thamar.dyeing.operation",
        "thamar_dyeing_batch_operation_rel",
        "batch_id",
        "operation_id",
        string="مراحل الخطط",
        required=True,
        tracking=True,
        domain="[('stage_type_id', '=', stage_type_id), ('company_id', '=', company_id)]",
    )
    work_order_ids = fields.Many2many(
        "thamar.dyeing.work.order",
        string="الخطط",
        compute="_compute_totals",
        store=True,
    )
    work_order_count = fields.Integer(
        string="عدد الخطط", compute="_compute_totals", store=True
    )
    operation_date = fields.Date(
        string="التاريخ", required=True, default=fields.Date.context_today, tracking=True
    )
    shift_supervisor_id = fields.Many2one(
        "res.users",
        string="رئيس الوردية",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    shift = fields.Selection(
        [("first", "الأولى"), ("second", "الثانية"), ("third", "الثالثة")],
        string="الوردية",
        required=True,
        default="first",
        tracking=True,
    )
    worker_name = fields.Char(string="اسم الفني / الموظف", tracking=True)
    entry_time = fields.Datetime(string="وقت الدخول", tracking=True)
    exit_time = fields.Datetime(string="وقت الخروج", tracking=True)
    duration_hours = fields.Float(
        string="الوقت المستهلك (ساعة)",
        compute="_compute_totals",
        store=True,
        digits=(16, 2),
    )
    total_weight_kg = fields.Float(
        string="إجمالي الوزن (كجم)",
        compute="_compute_totals",
        store=True,
        digits=(16, 3),
    )
    total_meter = fields.Float(
        string="إجمالي الأمتار",
        compute="_compute_totals",
        store=True,
        digits=(16, 2),
    )
    hourly_cost = fields.Monetary(
        string="تكلفة الساعة",
        related="machine_id.hourly_cost",
        store=True,
        readonly=True,
    )
    total_cost = fields.Monetary(
        string="تكلفة التشغيلة",
        compute="_compute_totals",
        store=True,
    )
    # Compatibility-only field for clients that still cache the previous view.
    # It is not displayed and never changes in data-entry mode.
    state = fields.Selection(
        [
            ("draft", "إدخال بيانات"),
            ("progress", "إدخال بيانات"),
            ("done", "إدخال بيانات"),
            ("cancelled", "إدخال بيانات"),
        ],
        string="الحالة التقنية",
        required=True,
        default="draft",
        copy=False,
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
        "operation_ids.work_order_id",
        "operation_ids.weight_kg",
        "operation_ids.meter",
        "entry_time",
        "exit_time",
        "hourly_cost",
    )
    def _compute_totals(self):
        for batch in self:
            batch.work_order_ids = batch.operation_ids.mapped("work_order_id")
            batch.work_order_count = len(batch.work_order_ids)
            batch.total_weight_kg = sum(batch.operation_ids.mapped("weight_kg"))
            batch.total_meter = sum(batch.operation_ids.mapped("meter"))
            duration = 0.0
            if batch.entry_time and batch.exit_time:
                duration = max(
                    (batch.exit_time - batch.entry_time).total_seconds() / 3600.0,
                    0.0,
                )
            batch.duration_hours = duration
            batch.total_cost = duration * batch.hourly_cost

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "جديد") == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "thamar.dyeing.batch"
                ) or "جديد"
        batches = super().create(vals_list)
        batches._sync_operations_from_batch()
        return batches

    def write(self, vals):
        result = super().write(vals)
        synchronized_fields = {
            "operation_ids",
            "machine_id",
            "operation_date",
            "shift",
            "shift_supervisor_id",
            "worker_name",
            "entry_time",
            "exit_time",
        }
        if synchronized_fields.intersection(vals):
            self._sync_operations_from_batch()
        return result

    def _sync_operations_from_batch(self):
        for batch in self:
            values = {
                "machine_id": batch.machine_id.id,
                "operation_date": batch.operation_date,
                "shift": batch.shift,
                "shift_supervisor_id": batch.shift_supervisor_id.id,
                "worker_name": batch.worker_name,
                "entry_time": batch.entry_time,
                "exit_time": batch.exit_time,
            }
            batch.operation_ids.with_context(from_machine_batch=True).write(values)

    @api.constrains("entry_time", "exit_time")
    def _check_times(self):
        for batch in self:
            if batch.entry_time and batch.exit_time and batch.exit_time < batch.entry_time:
                raise ValidationError("وقت الخروج يجب أن يكون بعد وقت الدخول.")

    @api.constrains("stage_type_id", "machine_id", "operation_ids")
    def _check_batch_configuration(self):
        for batch in self:
            if batch.stage_type_id and not batch.stage_type_id.allow_batching:
                raise ValidationError("هذه المرحلة غير مفعّل لها تجميع عدة خطط.")
            if batch.machine_id and batch.stage_type_id not in batch.machine_id.stage_type_ids:
                raise ValidationError("الماكينة المختارة غير مخصصة لهذه المرحلة.")
            if batch.operation_ids.filtered(
                lambda operation: operation.stage_type_id != batch.stage_type_id
            ):
                raise ValidationError("كل المراحل داخل التشغيلة يجب أن تكون من نفس النوع.")
            if (
                batch.machine_id.capacity_kg
                and batch.total_weight_kg > batch.machine_id.capacity_kg
            ):
                raise ValidationError(
                    "إجمالي وزن الخطط أكبر من حمولة الماكينة المختارة."
                )
            if len(batch.operation_ids.mapped("work_order_id")) != len(batch.operation_ids):
                raise ValidationError("لا يمكن إضافة مرحلتين من نفس الخطة إلى تشغيلة واحدة.")
            for operation in batch.operation_ids:
                other_batches = operation.batch_ids.filtered(lambda other: other != batch)
                if other_batches:
                    raise ValidationError(
                        "إحدى المراحل مرتبطة بالفعل بتشغيلة مجمعة أخرى."
                    )
