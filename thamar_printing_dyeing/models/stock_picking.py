# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_dyeing_material_issue = fields.Boolean(
        string="صرف مواد طباعة وصباغة",
        default=lambda self: bool(
            self.env.context.get("default_is_dyeing_material_issue")
        ),
        index=True,
        copy=False,
    )
    dyeing_work_order_id = fields.Many2one(
        "thamar.dyeing.work.order",
        string="الخطة",
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
    )
    dyeing_operation_id = fields.Many2one(
        "thamar.dyeing.operation",
        string="المرحلة",
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
        domain="[('work_order_id', '=', dyeing_work_order_id), ('company_id', '=', company_id)]",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if not self.env.context.get("default_is_dyeing_material_issue"):
            return values
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if "picking_type_id" in fields_list and not values.get("picking_type_id"):
            picking_type = warehouse.int_type_id or self.env[
                "stock.picking.type"
            ].search(
                [("code", "=", "internal"), ("company_id", "=", self.env.company.id)],
                limit=1,
            )
            values["picking_type_id"] = picking_type.id
        if "location_id" in fields_list and not values.get("location_id"):
            values["location_id"] = warehouse.lot_stock_id.id
        if "location_dest_id" in fields_list:
            production_location = self.env["stock.location"].search(
                [
                    ("usage", "=", "production"),
                    "|",
                    ("company_id", "=", self.env.company.id),
                    ("company_id", "=", False),
                ],
                order="company_id desc, id",
                limit=1,
            )
            if production_location:
                values["location_dest_id"] = production_location.id
        return values

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            operation_id = values.get("dyeing_operation_id")
            if operation_id:
                operation = self.env["thamar.dyeing.operation"].browse(operation_id)
                values["dyeing_work_order_id"] = operation.work_order_id.id
                values["is_dyeing_material_issue"] = True
                values.setdefault("origin", operation.work_order_id.name)
        return super().create(vals_list)

    @api.onchange("dyeing_work_order_id")
    def _onchange_dyeing_work_order_id(self):
        if (
            self.dyeing_operation_id
            and self.dyeing_operation_id.work_order_id != self.dyeing_work_order_id
        ):
            self.dyeing_operation_id = False

    @api.onchange("dyeing_operation_id")
    def _onchange_dyeing_operation_id(self):
        if self.dyeing_operation_id:
            self.dyeing_work_order_id = self.dyeing_operation_id.work_order_id
            self.origin = self.dyeing_operation_id.work_order_id.name

    @api.constrains(
        "is_dyeing_material_issue",
        "dyeing_work_order_id",
        "dyeing_operation_id",
        "company_id",
    )
    def _check_dyeing_material_issue_reference(self):
        for picking in self.filtered("is_dyeing_material_issue"):
            if not picking.dyeing_work_order_id or not picking.dyeing_operation_id:
                raise ValidationError(
                    "يجب اختيار الخطة والمرحلة عند صرف مواد الطباعة والصباغة."
                )
            if picking.dyeing_operation_id.work_order_id != picking.dyeing_work_order_id:
                raise ValidationError("المرحلة المختارة لا تتبع الخطة المحددة.")
            if picking.dyeing_work_order_id.company_id != picking.company_id:
                raise ValidationError("الخطة ومستند الصرف يجب أن يكونا في نفس الشركة.")


class StockMove(models.Model):
    _inherit = "stock.move"

    dyeing_operation_id = fields.Many2one(
        "thamar.dyeing.operation",
        string="مرحلة الطباعة والصباغة",
        related="picking_id.dyeing_operation_id",
        store=True,
        index=True,
    )
    dyeing_work_order_id = fields.Many2one(
        "thamar.dyeing.work.order",
        string="خطة الطباعة والصباغة",
        related="picking_id.dyeing_work_order_id",
        store=True,
        index=True,
    )
