# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DyeingMachine(models.Model):
    _name = "thamar.dyeing.machine"
    _description = "Printing and Dyeing Machine"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id"

    name = fields.Char(string="اسم الماكينة", required=True, tracking=True)
    code = fields.Char(string="كود الماكينة", tracking=True)
    stage_type_ids = fields.Many2many(
        "thamar.dyeing.stage.type",
        "thamar_dyeing_machine_stage_rel",
        "machine_id",
        "stage_type_id",
        string="المراحل التي تنفذها الماكينة",
        required=True,
        tracking=True,
    )
    capacity_kg = fields.Float(
        string="الحمولة (كجم)", digits=(16, 3), tracking=True
    )
    water_cost_hour = fields.Monetary(string="تكلفة المياه / ساعة")
    electricity_cost_hour = fields.Monetary(string="تكلفة الكهرباء / ساعة")
    gas_cost_hour = fields.Monetary(string="تكلفة الغاز / ساعة")
    other_cost_hour = fields.Monetary(string="تكاليف أخرى / ساعة")
    hourly_cost = fields.Monetary(
        string="قيمة الساعة",
        compute="_compute_hourly_cost",
        store=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="الشركة",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string="ملاحظات")

    @api.depends(
        "water_cost_hour",
        "electricity_cost_hour",
        "gas_cost_hour",
        "other_cost_hour",
    )
    def _compute_hourly_cost(self):
        for machine in self:
            machine.hourly_cost = (
                machine.water_cost_hour
                + machine.electricity_cost_hour
                + machine.gas_cost_hour
                + machine.other_cost_hour
            )

    @api.constrains(
        "capacity_kg",
        "water_cost_hour",
        "electricity_cost_hour",
        "gas_cost_hour",
        "other_cost_hour",
    )
    def _check_non_negative_values(self):
        for machine in self:
            values = (
                machine.capacity_kg,
                machine.water_cost_hour,
                machine.electricity_cost_hour,
                machine.gas_cost_hour,
                machine.other_cost_hour,
            )
            if any(value < 0 for value in values):
                raise ValidationError("الحمولة وتكاليف الماكينة لا يمكن أن تكون سالبة.")
