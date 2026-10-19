# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CheckBatch(models.Model):
    """Batch Portfolio Slip for receiving or disbursing/endorsing multiple checks at once."""
    _name = 'check.batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Check Batch Portfolio Slip / حافظة شيكات مجمعة'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Batch Number / رقم الحافظة',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        index=True
    )
    batch_type = fields.Selection([
        ('inward', 'حافظة استلام شيكات واردة (من عميل/مورد)'),
        ('outward', 'حافظة صرف وتظهير شيكات (لعميل/مورد)')
    ], string='Batch Type / نوع الحافظة', required=True, default='inward', tracking=True)

    date = fields.Date(
        string='Batch Date / تاريخ الحافظة',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner / الطرف (المسلم أو المستلم)',
        required=True,
        tracking=True,
        help='The partner delivering the batch (if inward) or receiving the endorsed checks (if outward).'
    )
    state = fields.Selection([
        ('draft', 'مسودة / Draft'),
        ('posted', 'معتمدة ومرحلة / Posted'),
        ('cancelled', 'ملغاة / Cancelled')
    ], string='Status / الحالة', default='draft', required=True, tracking=True, index=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company / الشركة',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency / العملة',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Cheque Journal / دفتر يومية الشيكات',
        domain="[('type', 'in', ('general', 'bank', 'cash'))]",
        compute='_compute_journal_id',
        store=True,
        readonly=False
    )
    account_id = fields.Many2one(
        'account.account',
        string='Partner Account / حساب الطرف للتسوية',
        compute='_compute_account_id',
        store=True,
        readonly=False,
        help='The counterpart receivable/payable account of the partner.'
    )

    # Inward lines
    inward_check_ids = fields.One2many(
        'account.check',
        'inward_batch_id',
        string='Checks / الشيكات المستلمة'
    )

    # Outward selection
    outward_check_ids = fields.Many2many(
        'account.check',
        'check_batch_outward_rel',
        'batch_id',
        'check_id',
        string='Checks to Disburse/Endorse / الشيكات المختارة للتظهير والصرف',
        domain="[('state', '=', 'in_safe'), ('check_type', '=', 'incoming')]"
    )

    total_amount = fields.Monetary(
        string='Total Amount / إجمالي الحافظة',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    checks_count = fields.Integer(
        string='Checks Count / عدد الشيكات',
        compute='_compute_totals',
        store=True
    )

    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry / القيد المحاسبي',
        readonly=True,
        copy=False
    )
    notes = fields.Text(string='Notes / ملاحظات')

    @api.depends('company_id')
    def _compute_journal_id(self):
        for batch in self:
            if not batch.journal_id:
                batch.journal_id = batch.company_id.check_journal_id or self.env['account.journal'].search([
                    ('company_id', '=', batch.company_id.id),
                    ('type', 'in', ('general', 'bank', 'cash'))
                ], limit=1)

    @api.depends('partner_id', 'batch_type')
    def _compute_account_id(self):
        for batch in self:
            if batch.partner_id:
                if batch.batch_type == 'inward':
                    # When receiving checks from partner, default to their receivable or payable
                    batch.account_id = (
                        batch.partner_id.property_account_receivable_id
                        or batch.partner_id.property_account_payable_id
                    )
                else:
                    # When paying partner with checks, default to their payable or receivable
                    batch.account_id = (
                        batch.partner_id.property_account_payable_id
                        or batch.partner_id.property_account_receivable_id
                    )

    @api.depends('batch_type', 'inward_check_ids.amount', 'outward_check_ids.amount')
    def _compute_totals(self):
        for batch in self:
            if batch.batch_type == 'inward':
                checks = batch.inward_check_ids
            else:
                checks = batch.outward_check_ids
            batch.total_amount = sum(checks.mapped('amount'))
            batch.checks_count = len(checks)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                b_type = vals.get('batch_type', 'inward')
                seq_code = 'check.batch.inward' if b_type == 'inward' else 'check.batch.outward'
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or _('New')
            partner_id = vals.get('partner_id')
            if partner_id and vals.get('inward_check_ids'):
                for cmd in vals['inward_check_ids']:
                    if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 0:
                        if isinstance(cmd[2], dict) and not cmd[2].get('partner_id'):
                            cmd[2]['partner_id'] = partner_id
        return super().create(vals_list)

    def write(self, vals):
        partner_id = vals.get('partner_id')
        if partner_id and vals.get('inward_check_ids'):
            for cmd in vals['inward_check_ids']:
                if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 0:
                    if isinstance(cmd[2], dict) and not cmd[2].get('partner_id'):
                        cmd[2]['partner_id'] = partner_id
        res = super().write(vals)
        if partner_id:
            for batch in self.filtered(lambda b: b.batch_type == 'inward'):
                batch.inward_check_ids.filtered(lambda c: not c.partner_id).write({'partner_id': partner_id})
        return res

    # -------------------------------------------------------------------------
    # POSTING & ACCOUNTING
    # -------------------------------------------------------------------------
    def action_post(self):
        """Validate the batch portfolio, create the journal entry, and update check statuses."""
        for batch in self:
            if batch.state != 'draft':
                continue

            if batch.batch_type == 'inward':
                checks = batch.inward_check_ids
                if not checks:
                    raise UserError(_("Please add at least one check to this inward batch."))
            else:
                checks = batch.outward_check_ids
                if not checks:
                    raise UserError(_("Please select at least one check to disburse/endorse."))
                # Verify that all selected checks are still in safe
                invalid_checks = checks.filtered(lambda c: c.state != 'in_safe')
                if invalid_checks:
                    names = ", ".join(invalid_checks.mapped('name'))
                    raise UserError(_("The following checks are no longer in safe: %s") % names)

            if batch.total_amount <= 0:
                raise UserError(_("Total batch amount must be greater than zero."))

            # Verify accounts configuration
            company = batch.company_id
            journal = batch.journal_id or company.check_journal_id
            if not journal:
                raise UserError(_("Please select a Cheque Journal in the batch or in Settings."))

            notes_receivable_acc = company.check_receivable_account_id
            if not notes_receivable_acc:
                # Attempt to find account with name containing "قبض"
                notes_receivable_acc = self.env['account.account'].search([
                    ('company_ids', 'in', company.id),
                    ('name', 'ilike', 'قبض')
                ], limit=1)
                if not notes_receivable_acc:
                    notes_receivable_acc = self.env['account.account'].search([
                        ('name', 'ilike', 'قبض')
                    ], limit=1)
                if not notes_receivable_acc:
                    raise UserError(_("Please configure the Notes Receivable Account (حساب أوراق القبض) in Cheque Settings."))

            partner_acc = batch.account_id or (
                batch.partner_id.property_account_receivable_id
                if batch.batch_type == 'inward'
                else batch.partner_id.property_account_payable_id
            )
            if not partner_acc:
                raise UserError(_("Please set a Counterpart Account for partner %s.") % batch.partner_id.name)

            # Filter financial checks (ignore pure guarantee checks for accounting)
            financial_checks = checks.filtered(lambda c: not c.is_guarantee)
            fin_total = sum(financial_checks.mapped('amount'))

            move = False
            if fin_total > 0:
                if batch.batch_type == 'inward':
                    # Entry:
                    # Debit: Notes Receivable Account (أوراق قبض - شيكات بالخزينة)
                    # Credit: Partner Account (حساب العميل أو المورد المسلم)
                    line_vals = [
                        {
                            'name': _("استلام حافظة شيكات %s - طرف: %s") % (batch.name, batch.partner_id.name),
                            'account_id': notes_receivable_acc.id,
                            'partner_id': batch.partner_id.id,
                            'debit': fin_total,
                            'credit': 0.0,
                        },
                        {
                            'name': _("تسوية حافظة شيكات %s") % batch.name,
                            'account_id': partner_acc.id,
                            'partner_id': batch.partner_id.id,
                            'debit': 0.0,
                            'credit': fin_total,
                        }
                    ]
                else:
                    # Entry for Outward / Endorsement:
                    # Debit: Target Partner Account (المستفيد المسلم له)
                    # Credit: Notes Receivable Account (أوراق قبض - خروج من الخزينة)
                    line_vals = [
                        {
                            'name': _("صرف وتظهير شيكات بحافظة %s إلى: %s") % (batch.name, batch.partner_id.name),
                            'account_id': partner_acc.id,
                            'partner_id': batch.partner_id.id,
                            'debit': fin_total,
                            'credit': 0.0,
                        },
                        {
                            'name': _("خروج شيكات مظهرة من الخزينة بحافظة %s") % batch.name,
                            'account_id': notes_receivable_acc.id,
                            'partner_id': batch.partner_id.id,
                            'debit': 0.0,
                            'credit': fin_total,
                        }
                    ]

                move = self.env['account.move'].create({
                    'move_type': 'entry',
                    'date': batch.date,
                    'journal_id': journal.id,
                    'ref': batch.name,
                    'line_ids': [(0, 0, lv) for lv in line_vals],
                })
                move.action_post()
                batch.move_id = move.id

            # Update checks
            if batch.batch_type == 'inward':
                for check in checks:
                    check_vals = {
                        'state': 'in_safe',
                        'partner_id': batch.partner_id.id,
                    }
                    if move:
                        check_vals['move_ids'] = [(4, move.id)]
                    check.write(check_vals)
            else:
                for check in checks:
                    check_vals = {
                        'state': 'endorsed',
                        'current_partner_id': batch.partner_id.id,
                        'endorse_date': batch.date,
                        'outward_batch_id': batch.id,
                    }
                    if move:
                        check_vals['move_ids'] = [(4, move.id)]
                    check.write(check_vals)

            batch.write({'state': 'posted'})

    def action_cancel(self):
        """Cancel batch and reverse changes if move exists."""
        for batch in self:
            if batch.move_id:
                if batch.move_id.state == 'posted':
                    batch.move_id.button_draft()
                    batch.move_id.button_cancel()
            if batch.batch_type == 'inward':
                batch.inward_check_ids.write({'state': 'cancelled'})
            else:
                batch.outward_check_ids.write({'state': 'in_safe', 'current_partner_id': False})
            batch.write({'state': 'cancelled'})

    def action_draft(self):
        """Reset batch to draft."""
        for batch in self:
            batch.write({'state': 'draft'})

    def action_view_move(self):
        self.ensure_one()
        return {
            'name': _('Journal Entry / القيد المحاسبي'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }
