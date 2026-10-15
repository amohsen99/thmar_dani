# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class CartellaLabelController(http.Controller):
    """
    Web-based label print view — replaces wkhtmltopdf PDF generation.
    Route: /cartella/label/<id>
    """

    @http.route(
        '/cartella/label/<int:record_id>',
        type='http',
        auth='user',
        methods=['GET'],
        sitemap=False,
    )
    def print_label(self, record_id, **kwargs):
        card = request.env['cartella.card'].sudo().browse(record_id)
        if not card.exists():
            return request.not_found()

        base_url = request.env['cartella.card']._get_public_base_url()

        return request.render(
            'thmar_textile_cartella.cartella_label_print_view',
            {
                'card': card,
                'base_url': base_url,
                'backend_url': f'{base_url}/odoo/cartella.card/{card.id}',
            },
        )
