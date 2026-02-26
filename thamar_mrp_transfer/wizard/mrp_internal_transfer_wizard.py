from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MrpInternalTransferWizard(models.TransientModel):
    _name = 'mrp.internal.transfer.wizard'
    _description = 'MRP Internal Transfer Wizard'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', required=True)
    line_ids = fields.One2many('mrp.internal.transfer.wizard.line', 'wizard_id', string='Components')
    source_location_id = fields.Many2one('stock.location', string='Source Location', required=True, domain="[('usage', '=', 'internal')]")
    dest_location_id = fields.Many2one('stock.location', string='Destination Location', required=True, domain="[('usage', '=', 'internal')]")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_id = self._context.get('active_id') or self._context.get('default_production_id')
        if active_id:
            production = self.env['mrp.production'].browse(active_id)
            res['production_id'] = production.id
            res['dest_location_id'] = production.location_src_id.id
        return res

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please add at least one component."))

        for line in self.line_ids:
            if line.quantity <= 0:
                raise UserError(_("Quantity for product %s must be greater than zero.") % line.product_id.display_name)

        # 1. Create Internal Transfer (One picking for all lines)
        source_warehouse = self.source_location_id.warehouse_id or self.production_id.picking_type_id.warehouse_id
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', source_warehouse.id)
        ], limit=1)
        
        if not picking_type:
             picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'origin': self.production_id.name,
            'move_type': 'direct',
        })

        for line in self.line_ids:
            # Create Stock Move for Transfer
            self.env['stock.move'].create({
                'description_picking': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom': line.uom_id.id,
                'product_uom_qty': line.quantity,
                'picking_id': picking.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.dest_location_id.id,
                'warehouse_id': picking_type.warehouse_id.id,
            })

            # 2. Add Component to MO (or update existing)
            existing_move = self.production_id.move_raw_ids.filtered(lambda m: m.product_id == line.product_id and m.state not in ('done', 'cancel'))
            if existing_move:
                existing_move[0].product_uom_qty += line.quantity
            else:
                self.env['stock.move'].create({
                    'description_picking': self.production_id.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'raw_material_production_id': self.production_id.id,
                    'location_id': self.production_id.location_src_id.id,
                    'location_dest_id': self.production_id.production_location_id.id,
                    'picking_type_id': self.production_id.picking_type_id.id,
                    'warehouse_id': self.production_id.picking_type_id.warehouse_id.id,
                    'company_id': self.production_id.company_id.id,
                    'state': 'confirmed',
                })
        
        picking.action_confirm()
        picking.action_assign()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Internal transfer created and components updated on MO.'),
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

class MrpInternalTransferWizardLine(models.TransientModel):
    _name = 'mrp.internal.transfer.wizard.line'
    _description = 'MRP Internal Transfer Wizard Line'

    wizard_id = fields.Many2one('mrp.internal.transfer.wizard', string='Wizard')
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('type', 'in', ['product', 'consu'])]")
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=False, store=True)
