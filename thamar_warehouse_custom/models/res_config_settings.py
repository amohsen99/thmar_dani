# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    transfer_validator_ids = fields.Many2many(
        'res.users',
        'transfer_validator_users_rel',
        'config_id',
        'user_id',
        string='Transfer Validators',
        help='Users who can validate any transfer in any warehouse, regardless of warehouse assignment'
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        validator_ids_str = params.get_param('thamar_warehouse_custom.transfer_validator_ids', '[]')
        try:
            validator_ids = eval(validator_ids_str) if validator_ids_str else []
        except:
            validator_ids = []
        res.update(transfer_validator_ids=[(6, 0, validator_ids)])
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('thamar_warehouse_custom.transfer_validator_ids', 
                        str(self.transfer_validator_ids.ids))

