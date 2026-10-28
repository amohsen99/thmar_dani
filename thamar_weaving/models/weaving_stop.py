# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WeavingStopReason(models.Model):
    _name = "thamar.weaving.stop.reason"
    _description = "Weaving Machine Stop Reason"
    _order = "sequence, name"

    name = fields.Char(string="سبب التوقف", required=True, translate=True)
    sequence = fields.Integer(string="الترتيب", default=10)
    stop_type = fields.Selection(
        [
            ("yarn_break", "قطع خيط / عيب غزل"),
            ("needle_break", "كسر إبر / جاك"),
            ("mechanical", "عطل ميكانيكي"),
            ("electrical", "عطل كهربائي"),
            ("setup", "تغيير عيار / خامة / ضبط مقاس"),
            ("maintenance", "صيانة وقائية / تزييت وتزييت"),
            ("shift_change", "تسليم وردية / نظافة"),
            ("power_cut", "انقطاع تيار كهربائي"),
            ("other", "أسباب أخرى"),
        ],
        string="نوع التوقف",
        default="mechanical",
        required=True,
    )
    active = fields.Boolean(default=True)


class WeavingMachineStop(models.Model):
    _name = "thamar.weaving.machine.stop"
    _description = "Weaving Machine Stop Log"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_time desc, id desc"

    machine_id = fields.Many2one(
        "thamar.weaving.machine",
        string="الماكينة",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    order_id = fields.Many2one(
        "thamar.weaving.order",
        string="أمر التشغيل المرتبط",
        ondelete="set null",
        tracking=True,
    )
    reason_id = fields.Many2one(
        "thamar.weaving.stop.reason",
        string="سبب التوقف",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    stop_type = fields.Selection(
        related="reason_id.stop_type",
        string="تصنيف التوقف",
        store=True,
        readonly=True,
    )
    start_time = fields.Datetime(
        string="وقت بدء التوقف",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    end_time = fields.Datetime(
        string="وقت نهاية التوقف",
        tracking=True,
    )
    duration_minutes = fields.Float(
        string="مدة التوقف (دقائق)",
        compute="_compute_duration",
        store=True,
    )
    technician_id = fields.Many2one(
        "res.users",
        string="الفني المسؤول",
        default=lambda self: self.env.user,
    )
    notes = fields.Text(string="تفاصيل العطل والإجراء المتخذ")
    company_id = fields.Many2one(
        "res.company",
        string="الشركة",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                diff = (rec.end_time - rec.start_time).total_seconds() / 60.0
                rec.duration_minutes = max(round(diff, 1), 0.0)
            else:
                rec.duration_minutes = 0.0

    @api.constrains("start_time", "end_time")
    def _check_dates(self):
        for rec in self:
            if rec.start_time and rec.end_time and rec.end_time < rec.start_time:
                raise ValidationError("وقت نهاية التوقف لا يمكن أن يكون قبل وقت البدء.")
