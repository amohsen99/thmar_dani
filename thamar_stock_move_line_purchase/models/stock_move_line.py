# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_compare


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # ── Related fields from Purchase Order Line ──
    # The chain is: stock.move.line → move_id → purchase_line_id (on stock.move)

    purchase_price_unit = fields.Float(
        string='Unit Price',
        compute='_compute_purchase_info',
        store=True,
        digits='Product Price',
    )
    purchase_discount = fields.Float(
        string='Discount (%)',
        compute='_compute_purchase_info',
        store=True,
        digits='Discount',
    )
    purchase_tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        compute='_compute_purchase_info',
        store=True,
    )
    purchase_total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_purchase_info',
        store=True,
        currency_field='purchase_currency_id',
    )
    purchase_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_purchase_info',
        store=True,
    )

    # ── On-hand & Income / Outcome quantities ──
    product_qty_available = fields.Float(
        string='On Hand Qty',
        related='product_id.qty_available',
        digits='Product Unit',
        readonly=True,
    )
    income_quantity = fields.Float(
        string='Income Qty',
        compute='_compute_income_outcome_qty',
        store=True,
        digits='Product Unit',
    )
    outcome_quantity = fields.Float(
        string='Outcome Qty',
        compute='_compute_income_outcome_qty',
        store=True,
        digits='Product Unit',
    )

    @api.depends(
        'quantity',
        'move_id.purchase_line_id',
        'move_id.purchase_line_id.price_unit',
        'move_id.purchase_line_id.discount',
        'move_id.purchase_line_id.tax_ids',
        'move_id.purchase_line_id.currency_id',
    )
    def _compute_purchase_info(self):
        for line in self:
            po_line = line.move_id.purchase_line_id
            if po_line:
                line.purchase_price_unit = po_line.price_unit
                line.purchase_discount = po_line.discount
                line.purchase_tax_ids = po_line.tax_ids
                line.purchase_currency_id = po_line.currency_id

                # Compute total: qty * price_unit * (1 - discount/100)
                price = po_line.price_unit * (1 - (po_line.discount or 0.0) / 100.0)
                subtotal = price * line.quantity

                # Apply taxes if any
                if po_line.tax_ids:
                    taxes = po_line.tax_ids.compute_all(
                        price,
                        currency=po_line.currency_id,
                        quantity=line.quantity,
                        product=line.product_id,
                        partner=line.move_id.picking_id.partner_id,
                    )
                    line.purchase_total_amount = taxes['total_included']
                else:
                    line.purchase_total_amount = subtotal
            else:
                line.purchase_price_unit = 0.0
                line.purchase_discount = 0.0
                line.purchase_tax_ids = False
                line.purchase_currency_id = False
                line.purchase_total_amount = 0.0

    @api.depends('quantity', 'location_id.usage', 'location_dest_id.usage', 'state')
    def _compute_income_outcome_qty(self):
        """Income = quantity entering internal/transit stock.
        Outcome = quantity leaving internal/transit stock."""
        for line in self:
            income = 0.0
            outcome = 0.0
            if line.state == 'done':
                src = line.location_id.usage
                dst = line.location_dest_id.usage
                internal = ('internal', 'transit')
                if src not in internal and dst in internal:
                    income = line.quantity
                elif src in internal and dst not in internal:
                    outcome = line.quantity
            line.income_quantity = income
            line.outcome_quantity = outcome
