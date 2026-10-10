# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class DyeingOperation(models.Model):
    _name = "thamar.dyeing.operation"
    _description = "Printing and Dyeing Operation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "work_order_id, sequence, id"

    name = fields.Char(
        string="رقم متابعة المرحلة",
        required=True,
        copy=False,
        readonly=True,
        default="جديد",
    )
    sequence = fields.Integer(string="الترتيب", default=10, index=True)
    work_order_id = fields.Many2one(
        "thamar.dyeing.work.order",
        string="الخطة",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    stage_type_id = fields.Many2one(
        "thamar.dyeing.stage.type",
        string="المرحلة",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    machine_id = fields.Many2one(
        "thamar.dyeing.machine",
        string="الماكينة",
        ondelete="restrict",
        tracking=True,
        domain="[('stage_type_ids', 'in', [stage_type_id]), ('company_id', '=', company_id)]",
    )
    # Kept only so stale browser/view caches can still read the old field.
    # It is hidden and never drives the data-entry workflow.
    state = fields.Selection(
        [
            ("waiting", "إدخال بيانات"),
            ("ready", "إدخال بيانات"),
            ("progress", "إدخال بيانات"),
            ("done", "إدخال بيانات"),
            ("cancelled", "إدخال بيانات"),
        ],
        string="الحالة التقنية",
        required=True,
        default="waiting",
        copy=False,
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
    operation_date = fields.Date(
        string="التاريخ",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="كود العميل",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    message_number = fields.Char(
        related="work_order_id.message_number",
        string="رقم الرسالة",
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        related="work_order_id.product_id",
        string="اسم الخام",
        store=True,
        readonly=True,
    )
    color_id = fields.Many2one(
        related="work_order_id.color_id",
        string="اللون",
        store=True,
        readonly=True,
    )
    design_id = fields.Many2one(
        related="work_order_id.design_id",
        string="رقم الرسمة",
        store=True,
        readonly=True,
    )
    printing_type_id = fields.Many2one(
        related="work_order_id.printing_type_id",
        string="نوع الطباعة",
        store=True,
        readonly=True,
    )
    dyeing_type_id = fields.Many2one(
        related="work_order_id.dyeing_type_id",
        string="نوع الصباغة",
        store=True,
        readonly=True,
    )
    weight_kg = fields.Float(
        string="الوزن الفعلي (كجم)", digits=(16, 3), tracking=True
    )
    meter = fields.Float(string="الأمتار الفعلية", digits=(16, 2), tracking=True)
    next_stage_type_id = fields.Many2one(
        "thamar.dyeing.stage.type",
        string="التوجيه بعد الانتهاء",
        ondelete="restrict",
        tracking=True,
    )
    batch_ids = fields.Many2many(
        "thamar.dyeing.batch",
        "thamar_dyeing_batch_operation_rel",
        "operation_id",
        "batch_id",
        string="التشغيلات المجمعة",
        readonly=True,
    )
    entry_time = fields.Datetime(string="وقت الدخول", tracking=True)
    exit_time = fields.Datetime(string="وقت الخروج", tracking=True)
    duration_hours = fields.Float(
        string="الوقت المستهلك (ساعة)",
        compute="_compute_duration_and_cost",
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
        string="تكلفة المرحلة",
        compute="_compute_duration_and_cost",
        store=True,
    )
    speed = fields.Float(string="السرعة", digits=(16, 2), tracking=True)
    temperature = fields.Float(string="الحرارة", digits=(16, 2), tracking=True)
    worker_name = fields.Char(string="اسم الفني / الموظف", tracking=True)
    notes = fields.Text(string="ملاحظات")
    company_id = fields.Many2one(
        related="work_order_id.company_id",
        string="الشركة",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    can_edit_customer = fields.Boolean(
        compute="_compute_can_edit_customer",
        string="يمكنه تعديل العميل",
    )

    @api.depends_context("uid")
    def _compute_can_edit_customer(self):
        can_edit = self.env.su or self.env.user.has_group(
            "thamar_printing_dyeing.group_printing_dyeing_manager"
        )
        for operation in self:
            operation.can_edit_customer = can_edit

    @api.depends(
        "entry_time",
        "exit_time",
        "hourly_cost",
        "weight_kg",
        "batch_ids.duration_hours",
        "batch_ids.total_weight_kg",
        "batch_ids.total_cost",
        "batch_ids.operation_ids",
    )
    def _compute_duration_and_cost(self):
        for operation in self:
            active_batch = operation.batch_ids[:1]
            if active_batch:
                operation.duration_hours = active_batch.duration_hours
                if active_batch.total_weight_kg:
                    cost_ratio = operation.weight_kg / active_batch.total_weight_kg
                else:
                    cost_ratio = 1.0 / len(active_batch.operation_ids)
                operation.total_cost = active_batch.total_cost * cost_ratio
                continue
            duration = 0.0
            if operation.entry_time and operation.exit_time:
                delta = operation.exit_time - operation.entry_time
                duration = max(delta.total_seconds() / 3600.0, 0.0)
            operation.duration_hours = duration
            operation.total_cost = duration * operation.hourly_cost

    @api.constrains("entry_time", "exit_time")
    def _check_operation_times(self):
        for operation in self:
            if (
                operation.entry_time
                and operation.exit_time
                and operation.exit_time < operation.entry_time
            ):
                raise ValidationError("وقت الخروج يجب أن يكون بعد وقت الدخول.")

    @api.constrains("weight_kg", "meter", "speed", "temperature")
    def _check_non_negative_values(self):
        for operation in self:
            if any(
                value < 0
                for value in (
                    operation.weight_kg,
                    operation.meter,
                    operation.speed,
                    operation.temperature,
                )
            ):
                raise ValidationError("الوزن والأمتار والسرعة والحرارة لا يمكن أن تكون سالبة.")

    @api.constrains("machine_id", "stage_type_id")
    def _check_machine_stage(self):
        for operation in self:
            if (
                operation.machine_id
                and operation.stage_type_id not in operation.machine_id.stage_type_ids
            ):
                raise ValidationError("الماكينة المختارة غير مخصصة لهذه المرحلة.")

    @api.model_create_multi
    def create(self, vals_list):
        actual_quantity_was_entered = [
            "weight_kg" in vals or "meter" in vals for vals in vals_list
        ]
        for vals in vals_list:
            order_id = vals.get("work_order_id")
            order = (
                self.env["thamar.dyeing.work.order"].browse(order_id)
                if order_id
                else self.env["thamar.dyeing.work.order"]
            )
            customer_was_changed = (
                vals.get("partner_id")
                and order
                and vals["partner_id"] != order.partner_id.id
            )
            if customer_was_changed and not (
                self.env.su
                or self.env.user.has_group(
                    "thamar_printing_dyeing.group_printing_dyeing_manager"
                )
            ):
                raise AccessError("تغيير العميل أثناء تنفيذ المراحل متاح للمدير فقط.")
            if vals.get("name", "جديد") == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "thamar.dyeing.operation"
                ) or "جديد"
            if vals.get("work_order_id"):
                vals.setdefault("partner_id", order.partner_id.id)
                vals.setdefault("operation_date", order.date)
                vals.setdefault(
                    "weight_kg",
                    order.actual_weight_kg
                    if order.actual_quantities_set
                    else order.planned_weight_kg,
                )
                vals.setdefault(
                    "meter",
                    order.actual_meter
                    if order.actual_quantities_set
                    else order.planned_meter,
                )
            if vals.get("work_order_id") and not vals.get("sequence"):
                last_operation = self.search(
                    [("work_order_id", "=", vals["work_order_id"])],
                    order="sequence desc, id desc",
                    limit=1,
                )
                vals["sequence"] = (last_operation.sequence or 0) + 10
        operations = super().create(vals_list)
        for operation, should_sync in zip(operations, actual_quantity_was_entered):
            if should_sync:
                operation._sync_actual_quantities_to_plan()
        return operations

    def write(self, vals):
        sensitive_fields = {
            "partner_id",
            "weight_kg",
            "meter",
            "entry_time",
            "exit_time",
        }
        if len(self) > 1 and sensitive_fields.intersection(vals):
            for operation in self:
                operation.write(dict(vals))
            return True

        customer_sync = self.env.context.get("sync_customer_from_plan")
        if "partner_id" in vals and not customer_sync and not (
            self.env.su
            or self.env.user.has_group(
                "thamar_printing_dyeing.group_printing_dyeing_manager"
            )
        ):
            raise AccessError("تغيير العميل أثناء تنفيذ المراحل متاح للمدير فقط.")

        old_customer = self.partner_id if self and "partner_id" in vals else False
        values = dict(vals)
        result = super().write(values)
        if self:
            if "partner_id" in values and not customer_sync:
                if old_customer != self.partner_id:
                    self.message_post(
                        body=_(
                            "تم تغيير العميل من %(old_customer)s إلى "
                            "%(new_customer)s بواسطة %(user)s.",
                            old_customer=old_customer.display_name or "-",
                            new_customer=self.partner_id.display_name or "-",
                            user=self.env.user.display_name,
                        )
                    )
                self.work_order_id.write({"partner_id": values["partner_id"]})
            if {"weight_kg", "meter"}.intersection(values):
                self._sync_actual_quantities_to_plan()
        return result

    def _sync_actual_quantities_to_plan(self):
        if self.env.context.get("skip_actual_quantity_sync"):
            return
        for operation in self.filtered(
            lambda record: record.stage_type_id.updates_actual_quantities
        ):
            operation.work_order_id.write(
                {
                    "actual_weight_kg": operation.weight_kg,
                    "actual_meter": operation.meter,
                    "actual_quantities_set": True,
                }
            )
            ordered_operations = operation.work_order_id.operation_ids.sorted(
                lambda record: (record.sequence, record.id)
            )
            operation_index = next(
                (
                    index
                    for index, ordered_operation in enumerate(ordered_operations)
                    if ordered_operation.id == operation.id
                ),
                -1,
            )
            if operation_index < 0:
                continue
            following_operations = ordered_operations[operation_index + 1 :]
            following_operations.with_context(skip_actual_quantity_sync=True).write(
                {"weight_kg": operation.weight_kg, "meter": operation.meter}
            )

    @api.onchange("work_order_id")
    def _onchange_work_order_id(self):
        if self.work_order_id:
            self.partner_id = self.work_order_id.partner_id
            self.operation_date = self.work_order_id.date
            self.weight_kg = (
                self.work_order_id.actual_weight_kg
                if self.work_order_id.actual_quantities_set
                else self.work_order_id.planned_weight_kg
            )
            self.meter = (
                self.work_order_id.actual_meter
                if self.work_order_id.actual_quantities_set
                else self.work_order_id.planned_meter
            )

    @api.onchange("stage_type_id")
    def _onchange_stage_type_id(self):
        if self.machine_id and self.stage_type_id not in self.machine_id.stage_type_ids:
            self.machine_id = False
