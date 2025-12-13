# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    qty_running = fields.Float(
        string='Running Quantity',
        compute='_compute_workcenter_quantities',
        digits='Product Unit of Measure',
        help='Total quantity currently being produced (timer started) in this workcenter'
    )
    
    qty_pending = fields.Float(
        string='Pending Quantity',
        compute='_compute_workcenter_quantities',
        digits='Product Unit of Measure',
        help='Total quantity waiting in this workcenter (not running yet)'
    )

    @api.depends('order_ids', 'order_ids.state', 'order_ids.qty_remaining', 'order_ids.time_ids', 'order_ids.time_ids.date_end')
    def _compute_workcenter_quantities(self):
        """
        Compute running and pending quantities for each workcenter.
        Running: work orders in 'progress' state (timer started)
        Pending: work orders in 'ready' or 'blocked' state (not started yet)
        """
        for workcenter in self:
            running_qty = 0.0
            pending_qty = 0.0
            
            for workorder in workcenter.order_ids:
                # Skip cancelled and done work orders
                if workorder.state in ('cancel', 'done'):
                    continue
                
                # Running: work orders in progress (timer started)
                if workorder.state == 'progress':
                    running_qty += workorder.qty_remaining
                
                # Pending: work orders ready or blocked (not started yet)
                elif workorder.state in ('ready', 'blocked'):
                    pending_qty += workorder.qty_remaining
            
            workcenter.qty_running = running_qty
            workcenter.qty_pending = pending_qty

