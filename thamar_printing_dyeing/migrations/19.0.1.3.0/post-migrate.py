# -*- coding: utf-8 -*-
"""Enable multi-plan machine batches for the dyehouse stage."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    dyehouse_stage = env.ref(
        "thamar_printing_dyeing.stage_type_dyehouse", raise_if_not_found=False
    )
    if dyehouse_stage:
        dyehouse_stage.allow_batching = True
