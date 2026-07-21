from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMoveExtension(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Source Picking',
        copy=False,
        readonly=True,
        help='The warehouse receipt or delivery order linked to this invoice/bill.',
    )
    picking_count = fields.Integer(
        string='Picking Count',
        compute='_compute_picking_count',
    )

    @api.depends('picking_id')
    def _compute_picking_count(self):
        for move in self:
            move.picking_count = 1 if move.picking_id else 0

    def action_view_linked_picking(self):
        """Smart-button action: open the linked picking form."""
        self.ensure_one()
        if not self.picking_id:
            raise UserError("No picking is linked to this invoice/bill.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Receipt / Delivery',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
            'target': 'current',
        }
