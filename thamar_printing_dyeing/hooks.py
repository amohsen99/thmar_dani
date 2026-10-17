# -*- coding: utf-8 -*-


def post_init_hook(env):
    env["stock.warehouse"]._sync_dyeing_warehouse_menus()
