# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

try:
    from num2words import num2words
except ImportError:
    num2words = None


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'analytic.mixin']

    # Cheque/Bank fields
    bank_id = fields.Many2one(
        'res.bank',
        string='Bank',
        help='Bank for cheque payment'
    )
    cheque_due_date = fields.Date(
        string='Cheque Due Date',
        help='Due date for cheque payment'
    )
    cheque_number = fields.Char(
        string='Cheque Number',
        help='Cheque number for payment'
    )
    is_cheque_payment = fields.Boolean(
        string='Is Cheque Payment',
        compute='_compute_is_cheque_payment',
        store=True,
        help='Technical field to check if payment method is Cheque'
    )

    recipient_name = fields.Char(
        string='Recipient Name',
    )

    # Payment Sequence Number
    payment_sequence_number = fields.Char(
        string='Payment Sequence Number',
        readonly=True,
        copy=False,
        help='Auto-generated sequence number: separate sequences for inbound (receive) and outbound (send) payments.'
    )

    # Approval fields
    is_approved = fields.Boolean(
        string='Approved',
        default=False,
        tracking=True,
        copy=False,
        help='Payment must be approved by manager before confirmation.'
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_date = fields.Datetime(
        string='Approved Date',
        readonly=True,
        copy=False,
        tracking=True,
    )

    @api.depends('payment_method_line_id', 'payment_method_line_id.name')
    def _compute_is_cheque_payment(self):
        """
        Compute if the payment method is a cheque payment
        Checks if payment method name contains 'Cheque' or 'Check'
        """
        for payment in self:
            if payment.payment_method_line_id and payment.payment_method_line_id.name:
                method_name = payment.payment_method_line_id.name.lower()
                payment.is_cheque_payment = 'cheque' in method_name or 'check' in method_name or 'شيك' in method_name
            else:
                payment.is_cheque_payment = False

    def amount_to_text_arabic(self):
        """
        Convert amount to Arabic text
        Returns the amount in Arabic words
        """
        self.ensure_one()
        
        if num2words is None:
            return ""
        
        # Get the amount
        amount = self.amount
        
        # Split into integer and decimal parts
        integral = int(amount)
        fractional = int(round((amount - integral) * 100))
        
        # Get currency labels
        currency_unit = 'جنيه'
        currency_subunit ='قرش'
        
        # Convert to Arabic words
        try:
            # Convert integer part to Arabic
            integral_text = num2words(integral, lang='ar')
            
            if fractional > 0:
                # Convert fractional part to Arabic
                fractional_text = num2words(fractional, lang='ar')
                result = f"{integral_text} {currency_unit} و {fractional_text} {currency_subunit}"
            else:
                result = f"{integral_text} {currency_unit}"
            
            return result
            
        except Exception:
            # Fallback to English if Arabic fails
            return self.currency_id.amount_to_text(amount)
    
    def amount_to_text_with_lang(self):
        """
        Convert amount to text based on user's language
        """
        self.ensure_one()

        # Get user's language
        lang_code = self.env.user.lang or 'en_US'

        # If Arabic, use Arabic conversion
        if lang_code.startswith('ar'):
            return self.amount_to_text_arabic()
        else:
            # Use default Odoo conversion
            return self.currency_id.amount_to_text(self.amount)

    # ========== Approval Methods ==========

    def action_approve_payment(self):
        """
        Approve the payment.
        Manager approves the payment before it can be confirmed.
        Only for outbound payments (sending money).
        """
        for payment in self:
            if payment.state != 'draft':
                raise UserError(_('Only draft payments can be approved.'))
            if payment.is_approved:
                raise UserError(_('This payment is already approved.'))
            if payment.payment_type == 'inbound':
                raise UserError(_('Incoming payments do not require approval.'))

            payment.write({
                'is_approved': True,
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_reject_approval(self):
        """
        Reject/Remove approval from the payment.
        Only for outbound payments.
        """
        for payment in self:
            if payment.state != 'draft':
                raise UserError(_('Only draft payments can have approval removed.'))
            if payment.payment_type == 'inbound':
                raise UserError(_('Incoming payments do not require approval.'))

            payment.write({
                'is_approved': False,
                'approved_by': False,
                'approved_date': False,
            })

    def action_post(self):
        """
        Override action_post to check approval before posting.
        Only outbound payments (sending money) require approval.
        Inbound payments (receiving money) can be confirmed directly.
        Also assigns a sequence number based on payment type.
        """
        for payment in self:
            # Approval check disabled - payments can be confirmed directly
            pass

        res = super(AccountPayment, self).action_post()

        # Assign sequence number after successful posting
        for payment in self:
            if not payment.payment_sequence_number:
                if payment.payment_type == 'inbound':
                    seq_code = 'account.payment.inbound'
                else:
                    seq_code = 'account.payment.outbound'
                payment.payment_sequence_number = self.env['ir.sequence'].next_by_code(seq_code) or '/'

        return res

    def action_draft(self):
        """
        Override action_draft to reset approval when moving back to draft.
        Only for outbound payments.
        """
        res = super(AccountPayment, self).action_draft()

        # Reset approval when moving back to draft (only for outbound)
        if self.payment_type == 'outbound':
            self.write({
                'is_approved': False,
                'approved_by': False,
                'approved_date': False,
            })

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        """
        Extend _prepare_move_line_default_vals to include cheque fields
        """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance)
        
        for line in res:
            line.update({
                'bank_id': self.bank_id.id,
                'cheque_due_date': self.cheque_due_date,
                'cheque_number': self.cheque_number,
            })
        return res

    # ========== Unified Cashier/Treasury Screen Customizations ==========

    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        domain=[],
    )

    is_direct_expense = fields.Boolean(
        string="Is Direct Expense",
        compute="_compute_is_direct_expense",
        store=True,
    )

    @api.depends('destination_account_id')
    def _compute_is_direct_expense(self):
        for pay in self:
            pay.is_direct_expense = pay.destination_account_id and pay.destination_account_id.internal_group == 'expense'

    @api.depends('journal_id', 'partner_id', 'partner_type')
    def _compute_destination_account_id(self):
        # Store previously set manual expense accounts to prevent them being overwritten
        prev_accounts = {}
        for pay in self:
            if pay.destination_account_id and pay.destination_account_id.internal_group == 'expense':
                prev_accounts[pay] = pay.destination_account_id
        
        super()._compute_destination_account_id()
        
        for pay in self:
            if pay in prev_accounts:
                pay.destination_account_id = prev_accounts[pay]

    @api.depends('destination_account_id', 'partner_id', 'company_id')
    def _compute_analytic_distribution(self):
        for payment in self:
            distribution = self.env['account.analytic.distribution.model']._get_distribution({
                'partner_id': payment.partner_id.id,
                'partner_category_id': payment.partner_id.category_id.ids,
                'account_prefix': payment.destination_account_id.code,
                'company_id': payment.company_id.id,
            })
            payment.analytic_distribution = distribution or payment.analytic_distribution or False

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('analytic_distribution',)

    def _prepare_move_counterpart_lines(self, default_values):
        res = super()._prepare_move_counterpart_lines(default_values)
        for line in res:
            if self.analytic_distribution:
                line['analytic_distribution'] = self.analytic_distribution
        return res

    @api.model
    def _get_valid_payment_account_types(self):
        res = super()._get_valid_payment_account_types()
        return res + ['expense', 'expense_other', 'expense_depreciation', 'expense_direct_cost']

    @api.constrains('destination_account_id', 'analytic_distribution')
    def _check_analytic_distribution_required(self):
        for payment in self:
            if payment.state != 'draft':
                continue
            if payment.destination_account_id and payment.destination_account_id.internal_group == 'expense':
                if not payment.analytic_distribution:
                    raise ValidationError(_("Analytic distribution is required for direct expense payments."))

    @api.constrains('partner_id', 'destination_account_id')
    def _check_partner_required(self):
        for payment in self:
            if not payment.destination_account_id or payment.destination_account_id.internal_group != 'expense':
                if not payment.partner_id:
                    raise ValidationError(_("Partner is required for standard payments."))

    # ========== Combined Receipt ==========

    def action_print_combined_receipt(self):
        """
        Print a single combined PDF receipt for multiple selected payments.
        Validates that all selected payments belong to the same partner.
        """
        if not self:
            raise UserError(_("Please select at least one payment."))

        partners = self.mapped('partner_id')
        if len(partners) > 1:
            raise UserError(_(
                "عذراً يا هندسة! لا يمكن طباعة إيصال مجمع لعملاء مختلفين. "
                "يرجى تحديد مدفوعات لعميل واحد فقط."
            ))

        return self.env.ref(
            'thamar_invoice_custom.action_report_combined_payment_receipt'
        ).report_action(self)
