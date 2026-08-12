# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import operator as py_operator
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
OPERATORS = {
    '<': py_operator.lt,
    '>': py_operator.gt,
    '<=': py_operator.le,
    '>=': py_operator.ge,
    '=': py_operator.eq,
    '!=': py_operator.ne
}


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    secondary_uom = fields.Boolean(index=True, default=False, string='Secondary uom')
    secondary_uom_id = fields.Many2one('uom.uom', 'Secondary UOM',
        help="Secondary Unit of Measure for independent tracking (e.g. Pieces/Bolts). "
             "Can be from any UOM category.")
    secondary_uom_name = fields.Char(string='secondary UOM', related='secondary_uom_id.name', readonly=True)
    secondary_product_qty = fields.Float(string='Qty Available', compute='_compute_secondary_quantities', search='_search_secondary_qty_available')

    @api.depends(
        'product_variant_ids',
        'product_variant_ids.stock_move_ids.product_qty',
        'product_variant_ids.stock_move_ids.state',
    )
    @api.depends_context('company')
    def _compute_secondary_quantities(self):
        res = self._compute_secondary_quantities_dict()
        for template in self:
            template.secondary_product_qty = res[template.id]['secondary_product_qty']
            template.update({'secondary_product_qty': res[template.id]['secondary_product_qty']})

    def _is_cost_method_standard(self):
        return True

    def _compute_secondary_quantities_dict(self):
        variants_available = {
            p['id']: p for p in self.product_variant_ids.read(['secondary_product_qty'])
        }
        prod_available = {}
        for template in self:
            secondary_product_qty = 0
            for p in template.with_context(active_test=False).product_variant_ids:
                secondary_product_qty += p['secondary_product_qty']
            prod_available[template.id] = {
                'secondary_product_qty': secondary_product_qty,
            }
        return prod_available

    def _search_secondary_qty_available(self, operator, value):
        domain = [('qty_available', operator, value)]
        product_variant_query = self.env['product.product']._search(domain)
        return [('product_variant_ids', 'in', product_variant_query)]

    def action_secondary_open_quants(self):
        return self.with_context(active_test=False).product_variant_ids.filtered(lambda p: p.active or p.secondary_product_qty != 0).action_secondary_open_quants()


class Product(models.Model):
    _inherit = 'product.product'

    secondary_product_qty = fields.Float(string='Qty Available', compute='_compute_secondary_quantities', search='_search_secondary_qty_available')

    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state')
    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'location', 'warehouse',
    )
    def _compute_secondary_quantities(self):
        products = self.filtered(lambda p: p.type != 'service')
        res = products._compute_quantities_dict(self.env.context.get('lot_id'), self.env.context.get('owner_id'), self.env.context.get('package_id'), self.env.context.get('from_date'), self.env.context.get('to_date'))
        for product in products:
            product.secondary_product_qty = res[product.id]['secondary_product_qty']
        services = self - products
        services.secondary_product_qty = 0.0

    def _search_secondary_qty_available(self, operator, value):
        # In the very specific case we want to retrieve products with stock available, we only need
        # to use the quants, not the stock moves. Therefore, we bypass the usual
        # '_search_product_quantity' method and call '_search_qty_available_new' instead. This
        # allows better performances.
        if not ({'from_date', 'to_date'} & set(self.env.context.keys())):
            product_ids = self._search_qty_available_new(
                operator, value, self.env.context.get('lot_id'), self.env.context.get('owner_id'),
                self.env.context.get('package_id')
            )
            return [('id', 'in', product_ids)]
        return self._search_product_quantity(operator, value, 'secondary_product_qty')

    def _search_product_quantity(self, operator, value, field):
        # TDE FIXME: should probably clean the search methods
        # to prevent sql injections
        if field not in ('secondary_product_qty', 'qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty', 'free_qty'):
            raise UserError(_('Invalid domain left operand %s', field))
        if operator not in ('<', '>', '=', '!=', '<=', '>='):
            raise UserError(_('Invalid domain operator %s', operator))
        if not isinstance(value, (float, int)):
            raise UserError(_('Invalid domain right operand %s', value))

        # TODO: Still optimization possible when searching virtual quantities
        ids = []
        # Order the search on `id` to prevent the default order on the product name which slows
        # down the search because of the join on the translation table to get the translated names.
        for product in self.with_context(prefetch_fields=False).sudo().search([], order='id'):
            if OPERATORS[operator](product[field], value):
                ids.append(product.id)
        return [('id', 'in', ids)]

    def _search_qty_available_new(self, operator, value, lot_id=False, owner_id=False, package_id=False):
        ''' Optimized method which doesn't search on stock.moves, only on stock.quants. '''
        product_ids = set()
        domain_quant = self._get_domain_locations()[0]
        if lot_id:
            domain_quant.append(('lot_id', '=', lot_id))
        if owner_id:
            domain_quant.append(('owner_id', '=', owner_id))
        if package_id:
            domain_quant.append(('package_id', '=', package_id))
        quants_groupby = self.env['stock.quant'].read_group(domain_quant, ['product_id', 'quantity', 'secondary_quantity'], ['product_id'])
        for quant in quants_groupby:
            if OPERATORS[operator](quant['quantity'], value):
                product_ids.add(quant['product_id'][0])
        return list(product_ids)

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            date_date_expected_domain_from = [('date', '>=', from_date)]
            domain_move_in += date_date_expected_domain_from
            domain_move_out += date_date_expected_domain_from
        if to_date:
            date_date_expected_domain_to = [('date', '<=', to_date)]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to

        Move = self.env['stock.move'].with_context(active_test=False)
        Quant = self.env['stock.quant'].with_context(active_test=False)
        domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_in_res = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_in_todo, ['product_id'], ['product_qty:sum'])}
        moves_out_res = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_out_todo, ['product_id'], ['product_qty:sum'])}
        quants_res = {product.id: (quantity, reserved_quantity) for product, quantity, reserved_quantity in Quant._read_group(domain_quant, ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])}
        second_quants_res = {product.id: secondary_quantity for product, secondary_quantity in Quant._read_group(domain_quant, ['product_id'], ['secondary_quantity:sum'])}
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
            moves_in_res_past = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_in_done, ['product_id'], ['product_qty:sum'])}
            moves_out_res_past = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_out_done, ['product_id'], ['product_qty:sum'])}
            # For secondary qty in the past, we need secondary_quantity from moves
            moves_in_sec_past = {product.id: sec_qty for product, sec_qty in Move._read_group(domain_move_in_done, ['product_id'], ['secondary_done_qty:sum'])}
            moves_out_sec_past = {product.id: sec_qty for product, sec_qty in Move._read_group(domain_move_out_done, ['product_id'], ['secondary_done_qty:sum'])}

        res = dict()
        for product in self.with_context(prefetch_fields=False):
            origin_product_id = product._origin.id
            product_id = product.id
            if not origin_product_id:
                res[product_id] = dict.fromkeys(
                    ['qty_available', 'free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available', 'secondary_product_qty',],
                    0.0,
                )
                continue
            rounding = product.uom_id.rounding
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = quants_res.get(origin_product_id, [0.0])[0] - moves_in_res_past.get(origin_product_id, 0.0) + moves_out_res_past.get(origin_product_id, 0.0)
                second_qty_available = second_quants_res.get(origin_product_id, 0.0) - moves_in_sec_past.get(origin_product_id, 0.0) + moves_out_sec_past.get(origin_product_id, 0.0)
            else:
                qty_available = quants_res.get(origin_product_id, [0.0])[0]
                second_qty_available = second_quants_res.get(origin_product_id, 0.0)
            reserved_quantity = quants_res.get(origin_product_id, [False, 0.0])[1]
            res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
            res[product_id]['free_qty'] = float_round(qty_available - reserved_quantity, precision_rounding=rounding)
            res[product_id]['incoming_qty'] = float_round(moves_in_res.get(origin_product_id, 0.0), precision_rounding=rounding)
            res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(origin_product_id, 0.0), precision_rounding=rounding)
            res[product_id]['virtual_available'] = float_round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
                precision_rounding=rounding)
            res[product_id]['secondary_product_qty'] = second_qty_available

        return res

    def action_secondary_open_quants(self):
        domain = [('product_id', 'in', self.ids)]
        hide_location = not self.env.user.has_group('stock.group_stock_multi_locations')
        hide_lot = all(product.tracking == 'none' for product in self)
        self = self.with_context(
            hide_location=hide_location, hide_lot=hide_lot,
            no_at_date=True, search_default_on_hand=True,
        )

        # If user have rights to write on quant, we define the view as editable.
        if self.env.user.has_group('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=True)
            # Set default location id if multilocations is inactive
            if not self.env.user.has_group('stock.group_stock_multi_locations'):
                user_company = self.env.company
                warehouse = self.env['stock.warehouse'].sudo().search(
                    [('company_id', '=', user_company.id)], limit=1
                )
                if warehouse:
                    self = self.with_context(default_location_id=warehouse.lot_stock_id.id)
        # Set default product id if quants concern only one product
        if len(self) == 1:
            self = self.with_context(
                default_product_id=self.id,
                single_product=True
            )
        else:
            self = self.with_context(product_tmpl_ids=self.product_tmpl_id.ids)
        action = self.env['stock.quant'].action_view_inventory()
        action['domain'] = domain
        action["name"] = _('Update Quantity')
        return action