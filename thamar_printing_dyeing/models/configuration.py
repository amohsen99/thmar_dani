# -*- coding: utf-8 -*-
from odoo import fields, models


class DyeingStageType(models.Model):
    _name = "thamar.dyeing.stage.type"
    _description = "Printing and Dyeing Stage"
    _order = "sequence, id"

    name = fields.Char(string="اسم المرحلة", required=True, translate=True)
    code = fields.Char(string="كود المرحلة", required=True)
    sequence = fields.Integer(string="الترتيب الافتراضي", default=10)
    active = fields.Boolean(default=True)
    updates_actual_quantities = fields.Boolean(
        string="مرحلة إدخال الكميات الفعلية",
        help="عند إدخال الوزن والأمتار في هذه المرحلة، يتم تحديث الخطة وكل المراحل التالية.",
    )
    allow_batching = fields.Boolean(
        string="السماح بتجميع عدة خطط",
        help="يسمح بضم مراحل من أكثر من خطة في تشغيلة ماكينة واحدة، مثل تشغيلات الجيت.",
    )
    machine_ids = fields.Many2many(
        "thamar.dyeing.machine",
        "thamar_dyeing_machine_stage_rel",
        "stage_type_id",
        "machine_id",
        string="الماكينات",
    )
    notes = fields.Text(string="ملاحظات")

    _stage_code_unique = models.Constraint(
        "UNIQUE(code)", "كود المرحلة مستخدم من قبل."
    )


class DyeingColor(models.Model):
    _name = "thamar.dyeing.color"
    _description = "Fabric Color"
    _order = "name"

    name = fields.Char(string="اسم اللون", required=True, translate=True)
    code = fields.Char(string="كود اللون")
    active = fields.Boolean(default=True)


class DyeingDesign(models.Model):
    _name = "thamar.dyeing.design"
    _description = "Printing Design"
    _order = "name"

    name = fields.Char(string="رقم الرسمة", required=True)
    description = fields.Char(string="وصف الرسمة")
    active = fields.Boolean(default=True)


class PrintingType(models.Model):
    _name = "thamar.printing.type"
    _description = "Printing Type"
    _order = "name"

    name = fields.Char(string="نوع الطباعة", required=True, translate=True)
    active = fields.Boolean(default=True)


class DyeingType(models.Model):
    _name = "thamar.dyeing.type"
    _description = "Dyeing Type"
    _order = "name"

    name = fields.Char(string="نوع الصباغة", required=True, translate=True)
    active = fields.Boolean(default=True)
