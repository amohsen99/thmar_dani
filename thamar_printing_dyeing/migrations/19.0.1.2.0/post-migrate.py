# -*- coding: utf-8 -*-
"""Activate preparation quantity propagation and rename the plan sequence."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    preparation_stage = env.ref(
        "thamar_printing_dyeing.stage_type_preparation", raise_if_not_found=False
    )
    if preparation_stage:
        preparation_stage.updates_actual_quantities = True

    plan_sequence = env.ref(
        "thamar_printing_dyeing.seq_dyeing_work_order", raise_if_not_found=False
    )
    if plan_sequence:
        plan_sequence.write(
            {"name": "خطة تشغيل طباعة وصباغة", "prefix": "PLAN/%(year)s/"}
        )

