# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta


class CheckDashboard(models.Model):
    """Real-time Cheque Management Dashboard with KPIs, state counts, and quick actions."""
    _name = 'check.dashboard'
    _description = 'Cheque Cycle Dashboard / لوحة مؤشرات دورة الشيكات'

    name = fields.Char(string='Dashboard', default='لوحة متابعة الشيكات')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

    # Counts
    count_total = fields.Integer(string='Total Checks', compute='_compute_stats')
    amount_total = fields.Monetary(string='Total Amount', compute='_compute_stats', currency_field='currency_id')

    count_in_safe = fields.Integer(string='In Safe', compute='_compute_stats')
    amount_in_safe = fields.Monetary(string='In Safe Amount', compute='_compute_stats', currency_field='currency_id')

    count_deposited = fields.Integer(string='Under Collection', compute='_compute_stats')
    amount_deposited = fields.Monetary(string='Under Collection Amount', compute='_compute_stats', currency_field='currency_id')

    count_endorsed = fields.Integer(string='Endorsed', compute='_compute_stats')
    amount_endorsed = fields.Monetary(string='Endorsed Amount', compute='_compute_stats', currency_field='currency_id')

    count_cleared = fields.Integer(string='Cleared', compute='_compute_stats')
    amount_cleared = fields.Monetary(string='Cleared Amount', compute='_compute_stats', currency_field='currency_id')

    count_bounced = fields.Integer(string='Bounced', compute='_compute_stats')
    amount_bounced = fields.Monetary(string='Bounced Amount', compute='_compute_stats', currency_field='currency_id')

    count_overdue = fields.Integer(string='Overdue Checks', compute='_compute_stats')
    amount_overdue = fields.Monetary(string='Overdue Amount', compute='_compute_stats', currency_field='currency_id')

    count_due_this_week = fields.Integer(string='Due Within 7 Days', compute='_compute_stats')
    amount_due_this_week = fields.Monetary(string='Due Soon Amount', compute='_compute_stats', currency_field='currency_id')

    count_incoming = fields.Integer(string='Incoming Checks', compute='_compute_stats')
    count_outgoing = fields.Integer(string='Outgoing Checks', compute='_compute_stats')

    def _compute_stats(self):
        today = fields.Date.context_today(self)
        week_ahead = today + timedelta(days=7)
        Check = self.env['account.check']

        for rec in self:
            domain = [('company_id', '=', rec.company_id.id)]
            all_checks = Check.search(domain)

            rec.count_total = len(all_checks)
            rec.amount_total = sum(all_checks.mapped('amount'))

            in_safe = all_checks.filtered(lambda c: c.state == 'in_safe')
            rec.count_in_safe = len(in_safe)
            rec.amount_in_safe = sum(in_safe.mapped('amount'))

            deposited = all_checks.filtered(lambda c: c.state == 'deposited')
            rec.count_deposited = len(deposited)
            rec.amount_deposited = sum(deposited.mapped('amount'))

            endorsed = all_checks.filtered(lambda c: c.state == 'endorsed')
            rec.count_endorsed = len(endorsed)
            rec.amount_endorsed = sum(endorsed.mapped('amount'))

            cleared = all_checks.filtered(lambda c: c.state == 'cleared')
            rec.count_cleared = len(cleared)
            rec.amount_cleared = sum(cleared.mapped('amount'))

            bounced = all_checks.filtered(lambda c: c.state == 'bounced')
            rec.count_bounced = len(bounced)
            rec.amount_bounced = sum(bounced.mapped('amount'))

            overdue = all_checks.filtered(
                lambda c: c.due_date and c.due_date < today and c.state in ('in_safe', 'deposited')
            )
            rec.count_overdue = len(overdue)
            rec.amount_overdue = sum(overdue.mapped('amount'))

            due_soon = all_checks.filtered(
                lambda c: c.due_date and today <= c.due_date <= week_ahead and c.state in ('in_safe', 'deposited')
            )
            rec.count_due_this_week = len(due_soon)
            rec.amount_due_this_week = sum(due_soon.mapped('amount'))

            rec.count_incoming = len(all_checks.filtered(lambda c: c.check_type == 'incoming'))
            rec.count_outgoing = len(all_checks.filtered(lambda c: c.check_type == 'outgoing'))

    @api.model
    def get_or_create_dashboard(self):
        """Returns or creates the dashboard record for current company."""
        dashboard = self.search([('company_id', '=', self.env.company.id)], limit=1)
        if not dashboard:
            dashboard = self.create({'company_id': self.env.company.id, 'name': 'لوحة متابعة الشيكات'})
        return dashboard

    @api.model
    def action_open_dashboard(self):
        dashboard = self.get_or_create_dashboard()
        return {
            'name': _('Cheque Management Dashboard / لوحة متابعة دورة الشيكات'),
            'type': 'ir.actions.act_window',
            'res_model': 'check.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # FILTER ACTIONS FOR CARDS
    # -------------------------------------------------------------------------
    def _action_open_checks(self, name, domain):
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.check',
            'view_mode': 'list,kanban,form,pivot,graph',
            'domain': domain,
            'context': {'search_default_group_status': 1},
        }

    def action_view_in_safe(self):
        return self._action_open_checks(
            _('Checks In Safe (متاحة بالخزينة)'),
            [('company_id', '=', self.company_id.id), ('state', '=', 'in_safe')]
        )

    def action_view_deposited(self):
        return self._action_open_checks(
            _('Checks Under Collection (برسم التحصيل في البنك)'),
            [('company_id', '=', self.company_id.id), ('state', '=', 'deposited')]
        )

    def action_view_endorsed(self):
        return self._action_open_checks(
            _('Endorsed Checks (شيكات مظهرة لموردين أو عملاء)'),
            [('company_id', '=', self.company_id.id), ('state', '=', 'endorsed')]
        )

    def action_view_cleared(self):
        return self._action_open_checks(
            _('Cleared Checks (شيكات محصلة أو منصرفة)'),
            [('company_id', '=', self.company_id.id), ('state', '=', 'cleared')]
        )

    def action_view_bounced(self):
        return self._action_open_checks(
            _('Bounced / Returned Checks (شيكات مرتدة أو مرفوضة)'),
            [('company_id', '=', self.company_id.id), ('state', '=', 'bounced')]
        )

    def action_view_overdue(self):
        today = fields.Date.context_today(self)
        return self._action_open_checks(
            _('Overdue Checks (شيكات متأخرة تجاوزت موعد الاستحقاق)'),
            [
                ('company_id', '=', self.company_id.id),
                ('due_date', '<', today),
                ('state', 'in', ('in_safe', 'deposited'))
            ]
        )

    def action_view_due_this_week(self):
        today = fields.Date.context_today(self)
        week_ahead = today + timedelta(days=7)
        return self._action_open_checks(
            _('Checks Due Within 7 Days (شيكات تستحق خلال أسبوع)'),
            [
                ('company_id', '=', self.company_id.id),
                ('due_date', '>=', today),
                ('due_date', '<=', week_ahead),
                ('state', 'in', ('in_safe', 'deposited'))
            ]
        )

    def action_view_all(self):
        return self._action_open_checks(
            _('All Paper Checks (جميع الشيكات)'),
            [('company_id', '=', self.company_id.id)]
        )

    def action_create_inward_batch(self):
        return {
            'name': _('New Inward Cheques Batch / استلام حافظة شيكات واردة'),
            'type': 'ir.actions.act_window',
            'res_model': 'check.batch',
            'view_mode': 'form',
            'context': {'default_batch_type': 'inward'},
            'target': 'current',
        }

    def action_create_outward_batch(self):
        return {
            'name': _('New Outward / Endorsement Batch / صرف وتظهير شيكات'),
            'type': 'ir.actions.act_window',
            'res_model': 'check.batch',
            'view_mode': 'form',
            'context': {'default_batch_type': 'outward'},
            'target': 'current',
        }
