# -*- coding: utf-8 -*-
"""Convert legacy raw-material text values to product links before schema setup."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    cr.execute("SELECT to_regclass('public.thamar_dyeing_work_order')")
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT EXISTS (
            SELECT 1
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name = 'thamar_dyeing_work_order'
               AND column_name = 'raw_material_name'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        ALTER TABLE thamar_dyeing_work_order
        ADD COLUMN IF NOT EXISTS product_id integer
        """
    )
    cr.execute(
        """
        SELECT DISTINCT raw_material_name
          FROM thamar_dyeing_work_order
         WHERE product_id IS NULL
         ORDER BY raw_material_name
        """
    )
    material_names = [name or "خامة غير محددة" for (name,) in cr.fetchall()]
    env = api.Environment(cr, SUPERUSER_ID, {})
    Product = env["product.product"].with_context(active_test=False)
    for material_name in material_names:
        product = Product.search([("name", "=", material_name)], limit=1)
        if not product:
            product = Product.create({"name": material_name})
        cr.execute(
            """
            UPDATE thamar_dyeing_work_order
               SET product_id = %s
             WHERE product_id IS NULL
               AND COALESCE(raw_material_name, '') = %s
            """,
            (product.id, "" if material_name == "خامة غير محددة" else material_name),
        )
