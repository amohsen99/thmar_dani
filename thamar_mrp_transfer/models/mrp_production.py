from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    internal_transfer_count = fields.Integer(compute='_compute_internal_transfer_count')

    def _compute_internal_transfer_count(self):
        for production in self:
            production.internal_transfer_count = self.env['stock.picking'].search_count([
                ('origin', '=', production.name),
                ('picking_type_id.code', '=', 'internal')
            ])

    def action_view_internal_transfers(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        action['domain'] = [('origin', '=', self.name), ('picking_type_id.code', '=', 'internal')]
        action['context'] = {'default_origin': self.name}
        return action

    def action_open_internal_transfer_wizard(self):
        self.ensure_one()
        return {
            'name': 'Add Component with Transfer',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.internal.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
            }
        }
