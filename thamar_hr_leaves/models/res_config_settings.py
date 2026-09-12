# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    clinical_manager_id = fields.Many2one('hr.employee', related='company_id.clinical_manager_id', string='Clinical Manager', readonly=False, help='The Clinical Manager responsible for approving ill leaves for this company.')
