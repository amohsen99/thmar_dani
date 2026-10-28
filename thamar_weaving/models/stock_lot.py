# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    weaving_order_id = fields.Many2one(
        "thamar.weaving.order",
        string="أمر تشغيل النسيج",
        index=True,
        readonly=True,
        help="أمر تشغيل النسيج الذي تم إنتاج هذا اللوط من خلاله",
    )
    weaving_roll_id = fields.Many2one(
        "thamar.weaving.roll",
        string="ثوب النسيج الأصلي",
        index=True,
        readonly=True,
        help="الثوب المحدد المرتبط بهذا اللوط في مصنع النسيج",
    )
    weaving_machine_id = fields.Many2one(
        "thamar.weaving.machine",
        string="ماكينة النسيج",
        readonly=True,
        help="الماكينة التي تم نسج هذا اللوط عليها",
    )
    weaving_type = fields.Selection(
        [
            ("circular", "نسيج دائري"),
            ("rectangular", "نسيج مستطيل / مسطح"),
        ],
        string="نوع النسيج",
        readonly=True,
    )
    fabric_grade = fields.Selection(
        [
            ("grade_a", "درجة أولى (ممتاز)"),
            ("grade_b", "درجة ثانية"),
            ("scrap", "هالك / فضلات"),
        ],
        string="درجة جودة القماش",
        readonly=True,
    )
    net_weight_kg = fields.Float(
        string="الوزن الصافي للوت (كجم)",
        digits=(16, 3),
        readonly=True,
    )
    length_meter = fields.Float(
        string="طول اللوت (متر)",
        digits=(16, 2),
        readonly=True,
    )
    fabric_gsm = fields.Float(
        string="وزن المتر المربع (GSM)",
        digits=(16, 1),
        readonly=True,
    )
    fabric_width_cm = fields.Float(
        string="عرض القماش (سم)",
        digits=(16, 1),
        readonly=True,
    )
    yarn_lot_summary = fields.Char(
        string="لوطات ونمر الغزل المستخدم",
        readonly=True,
        help="بيان خيوط الغزل وأرقام لوطاتها المستخدمة في نسج هذا اللوط",
    )
