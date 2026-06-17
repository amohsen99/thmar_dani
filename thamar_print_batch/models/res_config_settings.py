# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    prevent_delete_print_batch = fields.Boolean(
        string="Prevent Deleting Print Batches",
        default=False,
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    prevent_delete_print_batch = fields.Boolean(
        related='company_id.prevent_delete_print_batch',
        readonly=False,
        string="Prevent Deleting Print Batches",
        help="If checked, users will not be able to delete any print batch records.",
    )
