# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountCheck(models.Model):
    """Represents an individual physical paper check (Note Receivable / Payable)."""
    _name = 'account.check'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Commercial Paper Cheque / شيك تجاري'
    _order = 'due_date asc, id desc'

    name = fields.Char(string='Check Number / رقم الشيك', required=True, copy=False, index=True, tracking=True)
    check_type = fields.Selection([
        ('incoming', 'شيك وارد (أوراق قبض)'),
        ('outgoing', 'شيك صادر (أوراق دفع)')
    ], string='Check Type / نوع الشيك', required=True, default='incoming', tracking=True)

    partner_id = fields.Many2one(
        'res.partner',
        string='Original Partner / الطرف المصدر الأصلي',
        tracking=True,
        compute='_compute_partner_id',
        store=True,
        readonly=False,
        help='The customer or vendor who originally handed over this check.'
    )
    current_partner_id = fields.Many2one(
        'res.partner',
        string='Current Beneficiary / المستفيد الحالي',
        tracking=True,
        help='The party who currently holds the check after endorsement / transfer.'
    )
    drawer = fields.Char(
        string='Drawer / الساحب المدون على الشيك',
        help='The drawer name written on the physical check (may differ from the partner).'
    )
    bank_id = fields.Many2one('res.bank', string='Drawee Bank / البنك المسحوب عليه')
    bank_branch = fields.Char(string='Bank Branch / الفرع')
    
    check_date = fields.Date(
        string='Issue Date / تاريخ التحرير',
        default=fields.Date.context_today
    )
    due_date = fields.Date(
        string='Due Date / تاريخ الاستحقاق',
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True
    )

    amount = fields.Monetary(
        string='Amount / المبلغ',
        required=True,
        currency_field='currency_id',
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency / العملة',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company / الشركة',
        required=True,
        default=lambda self: self.env.company
    )

    state = fields.Selection([
        ('draft', 'مسودة / Draft'),
        ('in_safe', 'في الخزينة / In Safe'),
        ('deposited', 'برسم التحصيل / Under Collection'),
        ('endorsed', 'مظهر للغير / Endorsed'),
        ('cleared', 'محصل أو منصرف / Cleared'),
        ('bounced', 'مرتد أو مرفوض / Bounced'),
        ('cancelled', 'ملغي / Cancelled')
    ], string='Status / الحالة', default='in_safe', required=True, tracking=True, index=True)

    is_guarantee = fields.Boolean(
        string='Guarantee Check / شيك ضمان أو أمانة',
        default=False,
        help='Guarantee checks do not generate financial journal entries until action is taken.'
    )

    # Physical Storage
    storage_drawer_id = fields.Many2one(
        'check.storage.drawer',
        string='Safe / Drawer (الخزينة / الدرج)',
        tracking=True
    )
    storage_division = fields.Char(string='Shelf / Folder (الخانة / الرف)')

    # Action / Tracking details
    deposit_date = fields.Date(string='Deposit Date / تاريخ الإيداع')
    deposit_bank_journal_id = fields.Many2one(
        'account.journal',
        string='Deposit Bank / بنك الإيداع',
        domain="[('type', '=', 'bank')]"
    )
    clear_date = fields.Date(string='Clear Date / تاريخ التحصيل أو الصرف')
    clear_journal_id = fields.Many2one(
        'account.journal',
        string='Clearing Journal / بنك أو خزينة التحصيل والصرف',
        domain="[('type', 'in', ('bank', 'cash'))]",
        tracking=True
    )
    bounce_date = fields.Date(string='Bounce Date / تاريخ الارتداد')
    bounce_reason = fields.Text(string='Bounce Reason / سبب الارتداد')
    endorse_date = fields.Date(string='Endorse Date / تاريخ التظهير')

    # Links to batches & accounting
    inward_batch_id = fields.Many2one(
        'check.batch',
        string='Inward Batch / حافظة الاستلام',
        ondelete='set null'
    )
    outward_batch_id = fields.Many2one(
        'check.batch',
        string='Outward Batch / حافظة الصرف والتظهير',
        ondelete='set null'
    )
    move_ids = fields.Many2many(
        'account.move',
        'account_check_move_rel',
        'check_id',
        'move_id',
        string='Journal Entries / القيود المحاسبية'
    )
    moves_count = fields.Integer(string='Entries Count', compute='_compute_moves_count')

    # Media & Notes
    check_image = fields.Binary(string='Check Scan / صورة الشيك')
    check_image_name = fields.Char(string='File Name')
    notes = fields.Text(string='Notes / ملاحظات')

    # Overdue Indicators
    is_overdue = fields.Boolean(
        string='Is Overdue / متأخر الاستحقاق',
        compute='_compute_is_overdue',
        search='_search_is_overdue'
    )
    days_to_due = fields.Integer(
        string='Days to Due / الأيام المتبقية',
        compute='_compute_days_to_due'
    )

    @api.depends('inward_batch_id.partner_id')
    def _compute_partner_id(self):
        for check in self:
            if not check.partner_id and check.inward_batch_id and check.inward_batch_id.partner_id:
                check.partner_id = check.inward_batch_id.partner_id

    @api.depends('due_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for check in self:
            check.is_overdue = bool(
                check.due_date and check.due_date < today and check.state in ('in_safe', 'deposited')
            )

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('due_date', '<', today), ('state', 'in', ('in_safe', 'deposited'))]
        return ['|', ('due_date', '>=', today), ('state', 'not in', ('in_safe', 'deposited'))]

    @api.depends('due_date')
    def _compute_days_to_due(self):
        today = fields.Date.context_today(self)
        for check in self:
            if check.due_date:
                delta = check.due_date - today
                check.days_to_due = delta.days
            else:
                check.days_to_due = 0

    @api.depends('move_ids')
    def _compute_moves_count(self):
        for check in self:
            check.moves_count = len(check.move_ids)

    @api.depends('name', 'partner_id.name', 'amount', 'currency_id.symbol')
    def _compute_display_name(self):
        for check in self:
            partner_name = check.partner_id.name or _('Unknown')
            symbol = check.currency_id.symbol or ''
            check.display_name = f"#{check.name or ''} - {partner_name} ({check.amount:,.2f} {symbol})".strip()

    def name_get(self):
        return [(check.id, check.display_name) for check in self]

    def amount_to_text_with_lang(self):
        """Convert check amount to words (Arabic or English)."""
        self.ensure_one()
        lang_code = self.env.user.lang or 'ar_001'
        try:
            from num2words import num2words
            if lang_code.startswith('ar'):
                amount = self.amount
                integral = int(amount)
                fractional = int(round((amount - integral) * 100))
                curr_name = self.currency_id.currency_unit_label or self.currency_id.name or 'جنيه'
                sub_name = self.currency_id.currency_subunit_label or 'قرش'
                integral_text = num2words(integral, lang='ar')
                if fractional > 0:
                    fractional_text = num2words(fractional, lang='ar')
                    return f"{integral_text} {curr_name} و {fractional_text} {sub_name}"
                return f"{integral_text} {curr_name}"
            return self.currency_id.amount_to_text(self.amount)
        except Exception:
            return self.currency_id.amount_to_text(self.amount)

    # -------------------------------------------------------------------------
    # ACTION METHODS / WIZARD LAUNCHERS (Single & Multi-Select Support)
    # -------------------------------------------------------------------------
    def action_deposit(self):
        """Open the Bank Deposit Wizard for selected check(s)."""
        checks = self.filtered(lambda c: c.state == 'in_safe' and c.check_type == 'incoming')
        if not checks:
            raise UserError(_("Please select incoming checks in safe to deposit. / يرجى اختيار شيكات واردة وبحالة في الخزينة للإيداع."))
        return {
            'name': _('Deposit Checks to Bank / إيداع الشيكات بالبنك برسم التحصيل'),
            'type': 'ir.actions.act_window',
            'res_model': 'check.deposit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_check_ids': [(6, 0, checks.ids)],
                'default_deposit_date': fields.Date.context_today(self),
                'active_ids': checks.ids,
            }
        }

    def action_clear(self):
        """Open the Clear / Collection Wizard for selected check(s)."""
        checks = self.filtered(lambda c: c.state in ('deposited', 'in_safe', 'endorsed'))
        if not checks:
            raise UserError(_("Selected check(s) cannot be cleared in their current status. / لا يمكن تحصيل أو صرف الشيكات المختارة في حالتها الحالية."))
        return {
            'name': _('Clear / Collect Checks / إثبات تحصيل أو صرف الشيكات'),
            'type': 'ir.actions.act_window',
            'res_model': 'check.clear.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_check_ids': [(6, 0, checks.ids)],
                'default_clear_date': fields.Date.context_today(self),
                'active_ids': checks.ids,
            }
        }

    def action_bounce(self):
        """Open the Bounce / Return Wizard for selected check(s)."""
        checks = self.filtered(lambda c: c.state in ('deposited', 'endorsed', 'in_safe'))
        if not checks:
            raise UserError(_("Only deposited, endorsed, or in-safe checks can be marked as bounced. / الشيكات المودعة أو المظهرة أو في الخزينة فقط يمكن إثبات ارتدادها."))
        return {
            'name': _('Bounce / Return Checks / إثبات ارتداد الشيكات'),
            'type': 'ir.actions.act_window',
            'res_model': 'check.bounce.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_check_ids': [(6, 0, checks.ids)],
                'default_bounce_date': fields.Date.context_today(self),
                'active_ids': checks.ids,
            }
        }

    def action_endorse(self):
        """Open the Endorsement Wizard for selected check(s)."""
        checks = self.filtered(lambda c: c.state == 'in_safe' and c.check_type == 'incoming')
        if not checks:
            raise UserError(_("Only incoming checks in safe can be endorsed to another partner. / الشيكات الواردة في الخزينة فقط يمكن تظهيرها لطرف آخر."))
        return {
            'name': _('Endorse Checks to Partner / تظهير وتسليم الشيكات لطرف آخر'),
            'type': 'ir.actions.act_window',
            'res_model': 'check.endorse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_check_ids': [(6, 0, checks.ids)],
                'default_endorse_date': fields.Date.context_today(self),
                'active_ids': checks.ids,
            }
        }

    def action_view_moves(self):
        """View all accounting journal entries linked to this check."""
        self.ensure_one()
        return {
            'name': _('Journal Entries / القيود المحاسبية'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_ids.ids)],
            'context': {'create': False},
        }

    def action_reset_to_safe(self):
        """Reset check(s) back to safe."""
        checks = self.filtered(lambda c: c.state not in ('in_safe', 'draft'))
        if not checks:
            raise UserError(_("Selected checks are already in safe or draft. / الشيكات المختارة بالفعل في الخزينة أو مسودة."))
        checks.write({'state': 'in_safe'})

    def action_cancel(self):
        """Cancel the check(s)."""
        checks = self.filtered(lambda c: c.state not in ('cancelled', 'cleared'))
        if not checks:
            raise UserError(_("Selected checks are already cancelled or cleared. / الشيكات المختارة بالفعل ملغاة أو محصلة."))
        checks.write({'state': 'cancelled'})

    def action_print_check(self):
        """Print the check voucher report for current or selected checks."""
        return self.env.ref('thmar_check_management.action_report_account_check').report_action(self)
