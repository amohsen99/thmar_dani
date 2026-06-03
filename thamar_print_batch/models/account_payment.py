# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    print_batch_id = fields.Many2one(
        'account.print.batch',
        string='Print Batch',
        copy=False,
        tracking=True,
        help='The print batch this payment belongs to.',
    )
    print_batch_name = fields.Char(
        string='Batch Serial',
        related='print_batch_id.name',
        store=True,
        readonly=True,
    )

    def action_add_to_new_print_batch(self):
        """
        Create a new print batch from selected payments
        and open its form view.
        Called from the payment list/form view.
        """
        if not self:
            return

        # Ensure all selected payments have the same type (inbound/outbound)
        payment_types = set(self.mapped('payment_type'))
        if len(payment_types) > 1:
            from odoo.exceptions import UserError
            raise UserError(_(
                "عذراً! لا يمكنك إنشاء مطبوعة مجمعة لمدفوعات ومقبوضات في نفس الوقت. "
                "يرجى تحديد عمليات من نفس النوع (صادر أو وارد) فقط."
            ))

        # Determine partner from selected payments
        partners = self.mapped('partner_id')
        partner_id = partners[0].id if len(partners) == 1 else False

        # Create the new batch and link all selected payments
        batch = self.env['account.print.batch'].create({
            'batch_type': list(payment_types)[0],
            'partner_id': partner_id,
            'payment_ids': [(6, 0, self.ids)],
        })

        # Open the new batch form view
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Batch'),
            'res_model': 'account.print.batch',
            'res_id': batch.id,
            'view_mode': 'form',
            'target': 'current',
        }
