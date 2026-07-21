from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPickingInvoice(models.Model):
    _inherit = 'stock.picking'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice/Bill',
        copy=False,
        readonly=True,
        help='The invoice or vendor bill linked to this picking.',
    )
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_count',
    )

    @api.depends('invoice_id')
    def _compute_invoice_count(self):
        for picking in self:
            picking.invoice_count = 1 if picking.invoice_id else 0

    def action_create_direct_invoice(self):
        """Create a Customer Invoice or Vendor Bill directly from a validated picking.

        - Outgoing (delivery): creates ``out_invoice`` (Customer Invoice).
        - Incoming (receipt): creates ``in_invoice`` (Vendor Bill).
        """
        self.ensure_one()

        if self.state != 'done':
            raise UserError("You can only create an invoice/bill for a validated (done) picking.")
        if self.invoice_id:
            raise UserError("An invoice/bill is already linked to this picking.")
        if not self.partner_id:
            raise UserError("Please set a partner on this picking before creating an invoice/bill.")

        picking_code = self.picking_type_id.code

        if picking_code == 'outgoing':
            move_type = 'out_invoice'
        elif picking_code == 'incoming':
            move_type = 'in_invoice'
        else:
            raise UserError(
                "Direct invoice creation is only supported for "
                "Delivery Orders (outgoing) and Receipts (incoming)."
            )

        # --- Build invoice line values ----------------------------------
        invoice_line_vals = []
        for move in self.move_ids.filtered(lambda m: m.state == 'done'):
            product = move.product_id
            if not product:
                continue

            # Price: sale price for outgoing, cost for incoming
            if move_type == 'out_invoice':
                price_unit = product.lst_price
            else:
                price_unit = product.standard_price

            invoice_line_vals.append((0, 0, {
                'product_id': product.id,
                'name': product.display_name,
                'quantity': move.quantity,
                'price_unit': price_unit,
            }))

        if not invoice_line_vals:
            raise UserError("No done stock moves with products found to invoice.")

        # --- Create the invoice / bill -----------------------------------
        invoice_vals = {
            'move_type': move_type,
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': invoice_line_vals,
            'picking_id': self.id,
        }

        invoice = self.env['account.move'].sudo().create(invoice_vals)
        self.invoice_id = invoice.id

        # --- Return the form view of the newly created document ----------
        return self._get_invoice_action(invoice)

    def action_view_linked_invoice(self):
        """Smart-button action: open the linked Invoice / Bill form."""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("No invoice or bill is linked to this picking.")
        return self._get_invoice_action(self.invoice_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_invoice_action(self, invoice):
        """Return an ``ir.actions.act_window`` dict that opens *invoice*."""
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }
        if invoice.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
            action['name'] = 'Customer Invoice'
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        else:
            action['name'] = 'Vendor Bill'
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        return action
