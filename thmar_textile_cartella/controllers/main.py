# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class CartellaController(http.Controller):
    """
    Public-facing mobile web page for cartella cards.
    Accessible by scanning the QR code — no Odoo login required.
    Route: /cartella/view/<id>
    """

    @http.route(
        '/cartella/view/<int:record_id>',
        type='http',
        auth='public',
        methods=['GET'],
        sitemap=False,
    )
    def view_cartella_card(self, record_id, **kwargs):
        card = request.env['cartella.card'].sudo().browse(record_id)
        if not card.exists():
            return request.not_found()

        base_url = request.env['cartella.card']._get_public_base_url()

        return request.render(
            'thmar_textile_cartella.cartella_card_public_page',
            {
                'card': card,
                'base_url': base_url,
                'backend_url': f'{base_url}/odoo/cartella.card/{card.id}',
            },
        )

    @http.route(
        '/cartella/print/<int:record_id>',
        type='http',
        auth='user',
        methods=['GET'],
        sitemap=False,
    )
    def print_cartella_card(self, record_id, **kwargs):
        card = request.env['cartella.card'].sudo().browse(record_id)
        if not card.exists():
            return request.not_found()

        return request.render(
            'thmar_textile_cartella.cartella_card_print_page',
            {'card': card},
        )
