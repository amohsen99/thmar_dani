from odoo import models, fields, api


class LogisticsContract(models.Model):
    _name = 'logistics.contract'
    _description = 'Import Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Contract No.', required=True, copy=False,
        readonly=True, default='New',
    )
    sc_no = fields.Char(string='SC Number', tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Supplier', required=True, tracking=True,
    )
    country_id = fields.Many2one('res.country', string='Country', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    total_amount = fields.Monetary(string='Total Amount', tracking=True)
    advance_amount = fields.Monetary(string='Advance Payment', tracking=True)
    balance_amount = fields.Monetary(
        string='Balance Payment', compute='_compute_balance', store=True,
    )
    bank_id = fields.Many2one('res.bank', string='Bank', tracking=True)
    bank_date = fields.Date(string='Bank Date')
    notes = fields.Text(string='Notes')

    shipment_ids = fields.One2many(
        'logistics.shipment', 'contract_id', string='Shipments',
    )
    shipment_count = fields.Integer(
        string='Shipments', compute='_compute_shipment_stats',
    )
    total_containers = fields.Integer(
        string='Containers', compute='_compute_shipment_stats',
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # ── Computed ──────────────────────────────────────────────

    @api.depends('total_amount', 'advance_amount')
    def _compute_balance(self):
        for rec in self:
            rec.balance_amount = rec.total_amount - rec.advance_amount

    @api.depends('shipment_ids', 'shipment_ids.container_line_ids',
                 'shipment_ids.container_line_ids.quantity')
    def _compute_shipment_stats(self):
        for rec in self:
            rec.shipment_count = len(rec.shipment_ids)
            rec.total_containers = sum(
                line.quantity
                for shipment in rec.shipment_ids
                for line in shipment.container_line_ids
            )

    # ── Sequence ─────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'logistics.contract') or 'New'
        return super().create(vals_list)

    # ── Workflow ─────────────────────────────────────────────

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_shipments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shipments',
            'res_model': 'logistics.shipment',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }
