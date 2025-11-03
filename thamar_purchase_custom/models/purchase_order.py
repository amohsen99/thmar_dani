from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')

    def button_confirm(self):
        # Prevent confirming if no attachment
        for order in self:
            if not order.attachment:
                raise UserError("You must upload an attachment before confirming the order.")
        # Then call the original confirm logic
        return super(PurchaseOrder, self).button_confirm()
