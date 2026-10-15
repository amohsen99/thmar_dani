# -*- coding: utf-8 -*-
import base64
import logging
from io import BytesIO

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

try:
    import qrcode
except ImportError:
    qrcode = None
    _logger.warning(
        "thmar_textile_cartella: 'qrcode' library is not installed. "
        "Install it via: pip install qrcode[pil]"
    )


class CartellaCard(models.Model):
    """الكارتيلات - Textile Cartella Card (Core Model)"""
    _name = 'cartella.card'
    _description = 'الكارتيلات'
    _rec_name = 'sequence_number'
    _order = 'sequence_number desc'

    # ─── Primary Fields ────────────────────────────────────────────────────────

    raw_material_detail = fields.Char(
        string='اسم المنتج الخام بالتفصيل',
    )
    finished_product_id = fields.Many2one(
        comodel_name='cartella.finished.product',
        string='اسم المنتج التام',
        required=True,
        ondelete='restrict',
    )
    category_id = fields.Many2one(
        comodel_name='cartella.category',
        string='الفئة',
        required=True,
        ondelete='restrict',
    )

    # ─── Blend Ratios ──────────────────────────────────────────────────────────

    cotton_ratio = fields.Float(
        string='نسبة القطن (%)',
        digits=(5, 2),
    )
    polyester_ratio = fields.Float(
        string='نسبة البوليستر (%)',
        digits=(5, 2),
    )
    lycra_ratio = fields.Float(
        string='نسبة الليكرا (%)',
        digits=(5, 2),
    )
    blend_ratio_id = fields.Char(
        string='نسبة الخلط',
        compute='_compute_blend_ratio',
        store=True,
    )

    # ─── Finished Product Specifications ───────────────────────────────────────

    finished_weight = fields.Char(
        string='وزن المنتج التام',
        
    )
    finished_width = fields.Char(
        string='عرض المنتج التام',
        
    )

    # ─── Raw Material Specifications ───────────────────────────────────────────

    raw_weight = fields.Char(
        string='وزن المنتج الخام',
    )
    raw_width = fields.Char(
        string='عرض المنتج الخام',
    )
    yarn_count = fields.Char(
        string='نمرة الخيط',
    )

    # ─── Reference / Code ──────────────────────────────────────────────────────

    reference = fields.Char(
        string='المرجع / الكود',
    )
    sequence_number = fields.Char(
        string='رقم تسلسلي',
        readonly=True,
        copy=False,
        default='جديد',
    )

    # ─── Computed Display Fields ───────────────────────────────────────────────

    finished_weight_display = fields.Char(
        string='وزن المنتج التام',
        compute='_compute_display_values',
        store=False,
    )
    finished_width_display = fields.Char(
        string='عرض المنتج التام',
        compute='_compute_display_values',
        store=False,
    )
    raw_weight_display = fields.Char(
        string='وزن المنتج الخام',
        compute='_compute_display_values',
        store=False,
    )
    raw_width_display = fields.Char(
        string='عرض المنتج الخام',
        compute='_compute_display_values',
        store=False,
    )

    # ─── Computed Fields ───────────────────────────────────────────────────────

    barcode = fields.Char(
        string='الباركود المولد',
        compute='_compute_barcode',
        store=True,
        index=True,
        copy=False,
    )
    record_url = fields.Char(
        string='رابط السجل',
        compute='_compute_record_url',
        store=False,
    )
    print_label_url = fields.Char(
        string='طباعة الملصق',
        compute='_compute_print_label_url',
        store=False,
    )
    barcode_src = fields.Char(
        string='مصدر صورة الباركود',
        compute='_compute_barcode_src',
        store=False,
    )
    qr_image = fields.Binary(
        string='صورة QR',
        compute='_compute_qr_image',
        store=False,
        attachment=False,
    )

    # ─── Compute: Barcode ──────────────────────────────────────────────────────

    @api.depends(
        'finished_product_id',
        'finished_product_id.code',
        'category_id',
        'category_id.code',
        'sequence_number',
    )
    def _compute_barcode(self):
        for rec in self:
            parts = []
            # Part 1: Finished Product Code
            if rec.finished_product_id and rec.finished_product_id.code:
                parts.append(rec.finished_product_id.code.strip())
            # Part 2: Category Code
            if rec.category_id and rec.category_id.code:
                parts.append(rec.category_id.code.strip())
            # Part 3: Sequence number (skip placeholder)
            seq = rec.sequence_number or ''
            if seq and seq != 'جديد':
                parts.append(seq.strip())

            rec.barcode = '-'.join(parts) if parts else ''

    # ─── Compute: Blend Ratio Text ─────────────────────────────────────────────

    @api.depends('cotton_ratio', 'polyester_ratio', 'lycra_ratio')
    def _compute_blend_ratio(self):
        for rec in self:
            parts = []
            if rec.cotton_ratio:
                parts.append(f"Cotton {rec.cotton_ratio}%")
            if rec.polyester_ratio:
                parts.append(f"Polyester {rec.polyester_ratio}%")
            if rec.lycra_ratio:
                parts.append(f"Lycra {rec.lycra_ratio}%")
            rec.blend_ratio_id = ' - '.join(parts) if parts else ''

    @api.depends('finished_weight', 'finished_width', 'raw_weight', 'raw_width')
    def _compute_display_values(self):
        for rec in self:
            rec.finished_weight_display = self._format_number(rec.finished_weight, 3)
            rec.finished_width_display = self._format_number(rec.finished_width, 2)
            rec.raw_weight_display = self._format_number(rec.raw_weight, 3)
            rec.raw_width_display = self._format_number(rec.raw_width, 2)

    @api.model
    def _format_number(self, value, decimals=2):
        if not value:
            return ''
        if isinstance(value, (int, float)):
            return f"{float(value):.{decimals}f}"
        return str(value).strip()

    # ─── Compute: Record URL (absolute URL for QR scanning from mobile) ─────────

    def _compute_record_url(self):
        for rec in self:
            if not rec.id:
                rec.record_url = ''
                continue
            base_url = self._get_public_base_url()
            rec.record_url = f"{base_url}/cartella/view/{rec.id}" if base_url else f"/cartella/view/{rec.id}"

    @api.model
    def _get_public_base_url(self):
        """
        استنتاج الـ base URL العام مع احترام:
        1) system parameter thmar_textile_cartella.public_base_url (manual override)
        2) web.base.url (إذا كان public)
        3) request headers (X-Forwarded-Host / Host) — يعمل خلف nginx بدون ضبط web.base.url
        """
        Param = self.env['ir.config_parameter'].sudo()
        override = Param.get_param('thmar_textile_cartella.public_base_url', '').rstrip('/')
        if override:
            return override
        web_base = Param.get_param('web.base.url', '').rstrip('/')
        if web_base and 'localhost' not in web_base and 'odoo:' not in web_base:
            return web_base
        try:
            from odoo.http import request
            hr = request.httprequest
            forwarded_host = hr.headers.get('X-Forwarded-Host')
            host = forwarded_host or hr.headers.get('Host') or hr.host
            scheme = (
                hr.headers.get('X-Forwarded-Proto')
                or ('https' if hr.is_secure else 'http')
            )
            if host:
                return f"{scheme}://{host}"
        except Exception:
            pass
        return web_base

    def _compute_print_label_url(self):
        for rec in self:
            if rec.id:
                rec.print_label_url = f"/cartella/print/{rec.id}"
            else:
                rec.print_label_url = ''

    def _compute_barcode_src(self):
        from urllib.parse import quote
        for rec in self:
            if not rec.record_url:
                rec.barcode_src = ''
                continue
            url = rec.record_url
            path = url
            for prefix in ('http://', 'https://'):
                if path.lower().startswith(prefix):
                    rest = path[len(prefix):]
                    slash = rest.find('/')
                    path = rest[slash:] if slash >= 0 else '/'
                    break
            if not path.startswith('/'):
                path = '/' + path
            rec.barcode_src = (
                "/report/barcode/?barcode_type=QR&value=%s&width=120&height=120"
                % quote(path, safe='')
            )

    def _compute_qr_image(self):
        """توليد QR كصورة PNG بصيغة Base64 — لا يعتمد على wkhtmltopdf أو web.base.url."""
        for rec in self:
            rec.qr_image = False
            if not rec.record_url or qrcode is None:
                continue
            try:
                qr = qrcode.QRCode(
                    version=None,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=6,
                    border=2,
                )
                qr.add_data(rec.record_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = BytesIO()
                img.save(buf, format='PNG')
                rec.qr_image = base64.b64encode(buf.getvalue())
            except Exception:
                _logger.exception(
                    "thmar_textile_cartella: failed to generate QR for record %s",
                    rec.id,
                )
                rec.qr_image = False

    # ─── ORM Overrides ─────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence_number') or vals['sequence_number'] == 'جديد':
                vals['sequence_number'] = self.env['ir.sequence'].next_by_code(
                    'cartella.card.sequence'
                ) or 'جديد'
        return super().create(vals_list)

    def _compute_display_name(self):
        """Override display name — replaces deprecated name_get() in Odoo 17+."""
        for rec in self:
            seq = rec.sequence_number or ''
            prod = rec.finished_product_id.name or ''
            if seq and seq != 'جديد' and prod:
                rec.display_name = f"{seq} - {prod}"
            elif prod:
                rec.display_name = prod
            else:
                rec.display_name = seq or str(rec.id)
