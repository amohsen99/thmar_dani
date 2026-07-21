from odoo import models, fields, api


class LogisticsContainerLine(models.Model):
    _name = 'logistics.container.line'
    _description = 'Container Line'
    _rec_name = 'container_no'

    shipment_id = fields.Many2one(
        'logistics.shipment', string='Shipment',
        required=True, ondelete='cascade',
    )
    quantity = fields.Integer(string='Quantity', required=True, default=1)
    container_type = fields.Selection([
        ('20', '20 ft'),
        ('40', '40 ft'),
        ('40hc', '40 ft HC'),
    ], string='Container Size', required=True, default='40')
    container_no = fields.Char(string='Container No.')
    seal_no = fields.Char(string='Seal No.')
    weight = fields.Float(string='Weight (kg)', digits=(12, 2))
    notes = fields.Text(string='Notes')

    # @api.depends('quantity', 'container_type')
    # def _compute_display_name(self):
    #     for line in self:
    #         size = dict(self._fields['container_type'].selection).get(
    #             line.container_type, '')
    #         line.display_name = f"{line.quantity}*{size}"
