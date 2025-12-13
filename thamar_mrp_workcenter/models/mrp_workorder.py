# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def button_start(self, raise_on_invalid_state=False):
        """
        Override button_start to add sequence dependency validation.
        Prevent starting a work order if previous work orders (lower sequence) are not done.
        """
        # Check sequence dependencies before starting
        self._check_sequence_dependency()
        
        # Call the original button_start method
        return super(MrpWorkorder, self).button_start(raise_on_invalid_state=raise_on_invalid_state)

    def _check_sequence_dependency(self):
        """
        Check if all previous work orders (with lower sequence) in the same MO are done.
        Raise UserError if any previous work order is not done.
        """
        for workorder in self:
            # Get all work orders from the same manufacturing order
            mo_workorders = self.env['mrp.workorder'].search([
                ('production_id', '=', workorder.production_id.id),
                ('id', '!=', workorder.id),  # Exclude current work order
                ('sequence', '<', workorder.sequence),  # Only previous work orders (lower sequence)
            ])
            
            # Check if any previous work order is not done
            not_done_workorders = mo_workorders.filtered(lambda wo: wo.state != 'done')
            
            if not_done_workorders:
                # Build error message with list of pending work orders
                pending_names = ', '.join(not_done_workorders.mapped('name'))
                raise UserError(_(
                    'Cannot start work order "%s" (sequence %s).\n\n'
                    'The following previous work orders must be completed first:\n%s'
                ) % (workorder.name, workorder.sequence, pending_names))

