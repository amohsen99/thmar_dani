from odoo import models, fields

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    operation_template_id = fields.Many2one('mrp.operation.template', string='Operation Template', ondelete='set null')
