# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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
    is_printed = fields.Boolean(
        string='Printed in Batch',
        compute='_compute_is_printed',
        store=True,
        help='Indicates whether this payment has been included in a print batch.',
    )

    @api.depends('print_batch_id')
    def _compute_is_printed(self):
        for payment in self:
            payment.is_printed = bool(payment.print_batch_id)

    # ==================== Actions ====================

    def action_open_print_batch(self):
        """Open the linked print batch form view (smart button action)."""
        self.ensure_one()
        if not self.print_batch_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Batch'),
            'res_model': 'account.print.batch',
            'res_id': self.print_batch_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

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
            raise UserError(_(
                "عذراً! لا يمكنك إنشاء مطبوعة مجمعة لمدفوعات ومقبوضات في نفس الوقت. "
                "يرجى تحديد عمليات من نفس النوع (صادر أو وارد) فقط."
            ))

        # Ensure all selected payments belong to the same company
        companies = self.mapped('company_id')
        if len(companies) > 1:
            raise UserError(_(
                "عذراً! لا يمكنك إنشاء مطبوعة مجمعة لعمليات تابعة لشركات مختلفة. "
                "يرجى تحديد عمليات من نفس الشركة فقط."
            ))

        # Check for payments already linked to another batch
        for payment in self:
            if payment.print_batch_id:
                raise ValidationError(
                    "عذراً يا هندسة! الحركة رقم (%s) تم إدراجها بالفعل في المطبوعة المجمعة رقم (%s). "
                    "لا يمكن تكرار طباعتها."
                    % (payment.name, payment.print_batch_id.name)
                )

        # Determine partner from selected payments
        partners = self.mapped('partner_id')
        partner_id = partners[0].id if len(partners) == 1 else False

        # Create the new batch and link all selected payments
        batch = self.env['account.print.batch'].create({
            'batch_type': list(payment_types)[0],
            'partner_id': partner_id,
            'company_id': self[0].company_id.id,
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
