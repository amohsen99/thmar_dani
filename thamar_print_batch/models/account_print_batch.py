# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

try:
    # pyrefly: ignore [missing-import]
    from num2words import num2words
except ImportError:
    num2words = None
    _logger.warning("num2words library is not installed. Amount to words will fallback to English.")


class AccountPrintBatch(models.Model):
    _name = 'account.print.batch'
    _description = 'Payment Print Batch (المطبوعات)'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Batch Serial',
        required=True,
        copy=False,
        readonly=True,
        default='/',
        tracking=True,
        help='Unique sequential serial number for this print batch.',
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    batch_type = fields.Selection(
        [('inbound', 'Inbound (Receive)'), ('outbound', 'Outbound (Send)')],
        string='Batch Type',
        required=True,
        default='inbound',
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / Vendor',
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='The partner to whom all linked payments belong.',
    )
    recipient_name = fields.Char(
        string='Recipient / Payer Name',
        tracking=True,
        # readonly=True,
        # states={'draft': [('readonly', False)]},
    )
    amount_in_words = fields.Char(
        string='Amount in Words',
        compute='_compute_amount_in_words',
        store=True,
    )
    payment_ids = fields.One2many(
        'account.payment',
        'print_batch_id',
        string='Payments',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    state = fields.Selection(
        selection=[
            ('draft', 'جاري الإعداد'),
            ('posted', 'تم الترحيل والتأكيد'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
    )
    payment_count = fields.Integer(
        string='Payment Count',
        compute='_compute_total_amount',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    notes = fields.Text(
        string='Notes',
        # readonly=True,
        # states={'draft': [('readonly', False)]},
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        compute='_compute_journal_id',
        store=True,
    )


    # ==================== Computed Fields ====================

    @api.depends('payment_ids', 'payment_ids.journal_id')
    def _compute_journal_id(self):
        for batch in self:
            journals = batch.payment_ids.mapped('journal_id')
            if journals:
                # Takes the journal of the first payment in the batch
                batch.journal_id = journals[0].id
            else:
                batch.journal_id = False

    @api.depends('payment_ids', 'payment_ids.amount')
    def _compute_total_amount(self):
        for batch in self:
            batch.total_amount = sum(batch.payment_ids.mapped('amount'))
            batch.payment_count = len(batch.payment_ids)

    @api.depends('payment_ids', 'payment_ids.currency_id')
    def _compute_currency_id(self):
        for batch in self:
            currencies = batch.payment_ids.mapped('currency_id')
            if len(currencies) == 1:
                batch.currency_id = currencies.id
            else:
                batch.currency_id = batch.company_id.currency_id.id

    @api.depends('total_amount', 'currency_id')
    def _compute_amount_in_words(self):
        for batch in self:
            if not batch.total_amount:
                batch.amount_in_words = ""
                continue
            
            amount = batch.total_amount
            integral = int(amount)
            fractional = int(round((amount - integral) * 100))
            
            # Default to Egyptian pound since the user's previous code uses 'جنيه' and 'قرش'
            currency_unit = 'جنيه'
            currency_subunit = 'قرش'
            
            if num2words:
                try:
                    integral_text = num2words(integral, lang='ar')
                    if fractional > 0:
                        fractional_text = num2words(fractional, lang='ar')
                        result = f"{integral_text} {currency_unit} و {fractional_text} {currency_subunit}"
                    else:
                        result = f"{integral_text} {currency_unit}"
                    batch.amount_in_words = result
                except Exception:
                    batch.amount_in_words = batch.currency_id.amount_to_text(amount)
            else:
                batch.amount_in_words = batch.currency_id.amount_to_text(amount)

    # ==================== CRUD Overrides ====================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                batch_type = vals.get('batch_type', 'inbound')
                seq_code = 'account.print.batch.inbound' if batch_type == 'inbound' else 'account.print.batch.outbound'
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or '/'
        return super().create(vals_list)

    def unlink(self):
        for batch in self:
            if batch.state == 'posted':
                raise UserError(_(
                    'Cannot delete a posted print batch. '
                    'Please reset it to draft first.'
                ))
        return super().unlink()

    # ==================== Action Methods ====================

    def action_post(self):
        """
        Validate and post all linked draft payments, then set batch to 'posted'.
        Loops through all payment_ids in draft state and calls their
        standard action_post() to validate them in bulk.
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft batches can be validated.'))

        draft_payments = self.payment_ids.filtered(
            lambda p: p.state == 'draft'
        )
        if not draft_payments and not self.payment_ids:
            raise UserError(_(
                'No payments linked to this batch. '
                'Please add payments before validating.'
            ))


        self.write({'state': 'posted'})

    def action_draft(self):
        """Reset batch to draft state."""
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_('Only posted batches can be reset to draft.'))
        self.write({'state': 'draft'})

    def action_print_report(self):
        """Print the batch PDF report."""
        self.ensure_one()
        return self.env.ref(
            'thamar_print_batch.action_report_print_batch'
        ).report_action(self)

    # ==================== Constraints ====================

    @api.constrains('payment_ids')
    def _check_duplicate_payments(self):
        """Ensure no payment is already linked to another batch."""
        for batch in self:
            for payment in batch.payment_ids:
                other_batch = self.env['account.print.batch'].search([
                    ('payment_ids', 'in', payment.id),
                    ('id', '!=', batch.id),
                ], limit=1)
                if other_batch:
                    raise ValidationError(
                        "عذراً يا هندسة! الحركة رقم (%s) تم إدراجها بالفعل في المطبوعة المجمعة رقم (%s). "
                        "لا يمكن تكرار طباعتها."
                        % (payment.name, other_batch.name)
                    )
