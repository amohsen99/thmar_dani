# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockInventoryReportWizard(models.TransientModel):
    _name = 'stock.inventory.report.wizard'
    _description = 'Stock Inventory Report Wizard'

    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today,
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        help='Leave empty to include all storable products.',
    )
    product_category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        help='Filter by product category.',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]",
        help='Filter by specific warehouse location. Leave empty for all internal locations.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    def action_generate_report(self):
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(_('Start Date must be before or equal to End Date.'))

        # ── Build product domain ──
        product_domain = [('type', '=', 'consu'), ('is_storable', '=', True)]
        if self.product_ids:
            product_domain.append(('id', 'in', self.product_ids.ids))
        if self.product_category_id:
            product_domain.append(('categ_id', 'child_of', self.product_category_id.id))

        products = self.env['product.product'].search(product_domain)
        if not products:
            raise UserError(_('No storable products found for the given filters.'))

        # ── Build location filter ──
        if self.location_id:
            internal_location_ids = self.location_id.ids
        else:
            internal_location_ids = self.env['stock.location'].search(
                [('usage', '=', 'internal'), ('company_id', '=', self.company_id.id)]
            ).ids

        # ── Query: initial balance (all done moves BEFORE date_from) ──
        # Income  = destination is internal, source is NOT internal
        # Outcome = source is internal, destination is NOT internal
        self.env.cr.execute("""
            SELECT
                sml.product_id,
                COALESCE(SUM(CASE
                    WHEN sl_dest.usage IN ('internal','transit')
                     AND sl_src.usage  NOT IN ('internal','transit')
                    THEN sml.quantity ELSE 0 END), 0)
                -
                COALESCE(SUM(CASE
                    WHEN sl_src.usage  IN ('internal','transit')
                     AND sl_dest.usage NOT IN ('internal','transit')
                    THEN sml.quantity ELSE 0 END), 0)
                AS initial_balance
            FROM stock_move_line sml
            JOIN stock_location sl_src  ON sl_src.id  = sml.location_id
            JOIN stock_location sl_dest ON sl_dest.id = sml.location_dest_id
            WHERE sml.state = 'done'
              AND sml.product_id IN %s
              AND sml.date < %s
              AND (sml.location_id IN %s OR sml.location_dest_id IN %s)
            GROUP BY sml.product_id
        """, (
            tuple(products.ids),
            self.date_from,
            tuple(internal_location_ids),
            tuple(internal_location_ids),
        ))
        initial_map = {row[0]: row[1] for row in self.env.cr.fetchall()}

        # ── Query: income & outcome within [date_from, date_to] ──
        self.env.cr.execute("""
            SELECT
                sml.product_id,
                COALESCE(SUM(CASE
                    WHEN sl_dest.usage IN ('internal','transit')
                     AND sl_src.usage  NOT IN ('internal','transit')
                    THEN sml.quantity ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE
                    WHEN sl_src.usage  IN ('internal','transit')
                     AND sl_dest.usage NOT IN ('internal','transit')
                    THEN sml.quantity ELSE 0 END), 0) AS total_outcome
            FROM stock_move_line sml
            JOIN stock_location sl_src  ON sl_src.id  = sml.location_id
            JOIN stock_location sl_dest ON sl_dest.id = sml.location_dest_id
            WHERE sml.state = 'done'
              AND sml.product_id IN %s
              AND sml.date >= %s
              AND sml.date <= %s
              AND (sml.location_id IN %s OR sml.location_dest_id IN %s)
            GROUP BY sml.product_id
        """, (
            tuple(products.ids),
            self.date_from,
            self.date_to,
            tuple(internal_location_ids),
            tuple(internal_location_ids),
        ))
        movement_map = {row[0]: {'income': row[1], 'outcome': row[2]}
                        for row in self.env.cr.fetchall()}

        # ── Clean old report lines for this wizard ──
        report_line_model = self.env['stock.inventory.report.line']
        report_line_model.search([('wizard_id', '=', self.id)]).unlink()

        # ── Create report lines ──
        vals_list = []
        for product in products:
            initial = initial_map.get(product.id, 0.0)
            income = movement_map.get(product.id, {}).get('income', 0.0)
            outcome = movement_map.get(product.id, {}).get('outcome', 0.0)
            end_qty = initial + income - outcome

            # Skip products with no movement and zero balance
            if not initial and not income and not outcome:
                continue

            vals_list.append({
                'wizard_id': self.id,
                'product_id': product.id,
                'initial_balance': initial,
                'total_income': income,
                'total_outcome': outcome,
                'end_quantity': end_qty,
                'uom_id': product.uom_id.id,
            })

        if not vals_list:
            raise UserError(_('No stock movements found for the given period and filters.'))

        report_line_model.create(vals_list)

        # ── Return action to show the report lines ──
        return {
            'name': _('Inventory Report: %s → %s') % (self.date_from, self.date_to),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.inventory.report.line',
            'view_mode': 'list',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'create': False, 'edit': False, 'delete': False},
            'target': 'current',
        }


class StockInventoryReportLine(models.TransientModel):
    _name = 'stock.inventory.report.line'
    _description = 'Stock Inventory Report Line'
    _order = 'product_id'

    wizard_id = fields.Many2one(
        'stock.inventory.report.wizard',
        string='Wizard',
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=True,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        readonly=True,
    )
    initial_balance = fields.Float(
        string='Initial Balance',
        readonly=True,
        digits='Product Unit',
    )
    total_income = fields.Float(
        string='Total Income',
        readonly=True,
        digits='Product Unit',
    )
    total_outcome = fields.Float(
        string='Total Outcome',
        readonly=True,
        digits='Product Unit',
    )
    end_quantity = fields.Float(
        string='End Quantity',
        readonly=True,
        digits='Product Unit',
    )
