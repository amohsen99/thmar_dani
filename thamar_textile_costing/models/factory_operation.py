from odoo import fields, models


class Operation(models.Model):
    _name = 'factory.operation'
    _description = 'مرحلة تشغيل'
    name = fields.Char('المرحلة', required=True)
    kind = fields.Selection([('dye', 'صباغة'), ('finish', 'تجهيز')], required=True, default='finish', string='التصنيف')
    active = fields.Boolean(default=True)
