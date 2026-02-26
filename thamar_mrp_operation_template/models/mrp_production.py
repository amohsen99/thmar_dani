from odoo import models, fields, api, _

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    operation_template_ids = fields.Many2many(
        'mrp.operation.template',
        'mrp_production_operation_template_rel',
        'production_id',
        'template_id',
        string='Operation Templates'
    )

    def action_apply_operation_templates(self):
        """
        Create MO-level operations (routing lines) and Quality Points
        from the selected templates.
        """
        self.ensure_one()
        if not self.operation_template_ids:
            return

        Routing = self.env['mrp.routing.workcenter']
        QualityPoint = self.env['quality.point']

        # Determine start sequence (last existing sequence + 10)
        existing_ops = self.env['mrp.routing.workcenter'].search([('bom_id', '=', False)], order='sequence desc', limit=1)
        # However, for MO-level operations, they are usually linked to a BOM or created manually.
        # In this BOM-less approach, we will link them to the MO later if Odoo allows or just create them
        # so Odoo generates Work Orders.
        
        # Actually, in Odoo 19, mrp.routing.workcenter is linked to mrp.bom.
        # If we want MO-level operations without a BOM, we create mrp.workorder records directly.
        # BUT creating mrp.routing.workcenter without a bom_id might not be supported easily
        # as it has required=True on bom_id in Odoo core.
        
        # Checking Odoo 19 mrp_routing.py again...
        # 23:    bom_id = fields.Many2one(
        # 24:        'mrp.bom', 'Bill of Material',
        # 25:        index=True, ondelete='cascade', required=True, check_company=True)
        
        # Since bom_id is required, we have two options:
        # 1. Create a "dummy" BOM for every MO (not ideal).
        # 2. Create mrp.workorder records directly on the MO.
        
        # Let's go with option 2: Creating work orders directly on the MO.
        
        new_wos = []
        for template in self.operation_template_ids:
            wo_vals = {
                'name': template.name,
                'production_id': self.id,
                'workcenter_id': template.workcenter_id.id,
                'duration_expected': template.time_cycle_manual,
                'state': 'ready',
            }
            wo = self.env['mrp.workorder'].create(wo_vals)
            
            # Now handle Quality Points and Checks with chaining for Shop Floor support
            previous_check = self.env['quality.check']
            for qp_template in template.quality_point_ids:
                # We create a specific Quality Point for this MO/WO to ensure it triggers
                new_qp = qp_template.copy({
                    'product_ids': [(6, 0, self.product_id.ids)],
                    'picking_type_ids': [(6, 0, self.picking_type_id.ids)],
                    'company_id': self.company_id.id,
                    'operation_id': False, # mrp.routing.workcenter link (not used in BOM-less)
                })
                
                check = self.env['quality.check'].create({
                    'point_id': new_qp.id,
                    'production_id': self.id,
                    'workorder_id': wo.id,
                    'product_id': self.product_id.id,
                    'company_id': self.company_id.id,
                    'team_id': new_qp.team_id.id,
                    'test_type_id': new_qp.test_type_id.id,
                    'previous_check_id': previous_check.id,
                    'finished_product_sequence': wo.qty_produced,
                    'worksheet_document': new_qp.worksheet_document if hasattr(new_qp, 'worksheet_document') else False,
                })
                if previous_check:
                    previous_check.next_check_id = check
                previous_check = check

            # Set the first check as current for the tablet view
            if wo.check_ids:
                wo._change_quality_check(position='first')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Operations Applied'),
                'message': _('Selected templates have been applied to this Manufacturing Order.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }
