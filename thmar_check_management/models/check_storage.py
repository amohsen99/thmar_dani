# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CheckStorageDrawer(models.Model):
    """Represents a physical safe or drawer where paper checks are secured."""
    _name = 'check.storage.drawer'
    _description = 'Check Storage Drawer / Safe'
    _order = 'name'

    name = fields.Char(string='Safe / Drawer Name (اسم الخزينة أو الدرج)', required=True, translate=True)
    code = fields.Char(string='Code / الرمز')
    responsible_id = fields.Many2one('res.users', string='Responsible / المسؤول', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    description = fields.Text(string='Description / الوصف')
    check_ids = fields.One2many('account.check', 'storage_drawer_id', string='Checks / الشيكات')
    checks_count = fields.Integer(string='Current Checks Count', compute='_compute_checks_count')

    @api.depends('check_ids', 'check_ids.state')
    def _compute_checks_count(self):
        for drawer in self:
            drawer.checks_count = len(drawer.check_ids.filtered(lambda c: c.state == 'in_safe'))
