from odoo import models, fields

class MrpOperationTemplate(models.Model):
    _name = 'mrp.operation.template'
    _description = 'MRP Operation Template'
    _order = 'name'

    name = fields.Char('Operation', required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', required=True, check_company=True)
    time_cycle_manual = fields.Float('Manual Duration', default=60, help="Time in minutes")
    time_mode = fields.Selection([
        ('manual', 'Fixed'),
        ('auto', 'Computed')], string='Duration Computation',
        default='manual')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    description = fields.Text('Instructions')
    quality_point_ids = fields.Many2many('quality.point', string='Quality Points')
