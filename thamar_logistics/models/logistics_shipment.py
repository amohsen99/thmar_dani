from odoo import models, fields, api


class LogisticsShipment(models.Model):
    _name = 'logistics.shipment'
    _description = 'Import Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_shipping desc, id desc'

    name = fields.Char(
        string='Shipment Ref.', required=True, copy=False,
        readonly=True, default='New',
    )
    contract_id = fields.Many2one(
        'logistics.contract', string='Contract', tracking=True,
        ondelete='cascade',
    )
    acid_no = fields.Char(string='ACID No.', required=True, tracking=True)
    invoice_no = fields.Char(string='Invoice No.', tracking=True)
    bl_no = fields.Char(string='BL No.', tracking=True)

    # ── Supplier ─────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Supplier', tracking=True,
    )
    country_id = fields.Many2one('res.country', string='Country')

    # ── Goods ────────────────────────────────────────────────
    item_type = fields.Char(string='Item Type')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')

    # ── Containers ───────────────────────────────────────────
    container_line_ids = fields.One2many(
        'logistics.container.line', 'shipment_id', string='Containers',
    )
    total_containers = fields.Integer(
        string='Total Containers', compute='_compute_container_info',
        store=True,
    )
    container_summary = fields.Char(
        string='Container Summary', compute='_compute_container_info',
        store=True,
    )

    # ── Shipping ─────────────────────────────────────────────
    shipping_company_id = fields.Many2one(
        'logistics.shipping.company', string='Shipping Company', tracking=True,
    )
    port_loading_id = fields.Many2one(
        'logistics.port', string='Loading Port',
    )
    port_arrival_id = fields.Many2one(
        'logistics.port', string='Arrival Port',
    )
    date_shipping = fields.Date(string='Shipping Date', tracking=True)
    date_arrival = fields.Date(string='Arrival Date', tracking=True)

    # ── Financial ────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    total_amount = fields.Monetary(string='Total Amount', tracking=True)
    advance_amount = fields.Monetary(string='Advance Payment', tracking=True)
    balance_amount = fields.Monetary(
        string='Balance', compute='_compute_balance', store=True,
    )
    bank_id = fields.Many2one('res.bank', string='Bank', tracking=True)
    penalty_start_date = fields.Date(string='Penalty Start Date')

    # ── Operations ───────────────────────────────────────────
    customs_broker = fields.Char(string='Customs Broker')
    store_permit_no = fields.Char(string='Store Permit No.')
    deposit_done = fields.Boolean(string='Deposits Done')
    linking_done = fields.Boolean(string='Linking Done')

    # ── Status ───────────────────────────────────────────────
    state = fields.Selection([
        ('incoming', 'وارد'),
        ('bank', 'بنك'),
        ('clearance', 'تحت التخليص'),
        ('arrived', 'وصول المصنع'),
    ], string='Status', default='incoming', tracking=True)

    # ── Computed ─────────────────────────────────────────────

    @api.depends('total_amount', 'advance_amount')
    def _compute_balance(self):
        for rec in self:
            rec.balance_amount = rec.total_amount - rec.advance_amount

    @api.depends('container_line_ids', 'container_line_ids.quantity',
                 'container_line_ids.container_type')
    def _compute_container_info(self):
        for rec in self:
            lines = rec.container_line_ids
            rec.total_containers = sum(lines.mapped('quantity'))
            parts = []
            for line in lines:
                size_label = line.container_type or ''
                parts.append(f"{line.quantity}*{size_label}")
            rec.container_summary = ', '.join(parts) if parts else ''

    # ── Onchange ─────────────────────────────────────────────

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            self.partner_id = self.contract_id.partner_id
            self.country_id = self.contract_id.country_id
            self.bank_id = self.contract_id.bank_id

    # ── Sequence ─────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'logistics.shipment') or 'New'
        return super().create(vals_list)

    # ── Workflow ─────────────────────────────────────────────

    def action_to_bank(self):
        self.write({'state': 'bank'})

    def action_to_clearance(self):
        self.write({'state': 'clearance'})

    def action_to_arrived(self):
        self.write({'state': 'arrived'})

    def action_to_incoming(self):
        self.write({'state': 'incoming'})
