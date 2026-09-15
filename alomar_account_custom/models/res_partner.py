# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_code = fields.Char(
        string='Customer / Vendor Code',
        index=True,
    )
