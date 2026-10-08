# -*- coding: utf-8 -*-
"""Clean up views left behind by product modules removed from the codebase."""

import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Deactivate legacy views whose Python fields are no longer available.

    Old database backups can still contain active views from these modules even
    though their source code was removed.  Those views reference fields such as
    ``product.template.is_fabric`` and ``product.template.operation`` and make
    the product form/list fail in the web client.

    Only views owned by the two removed modules are deactivated.  Their data is
    intentionally left in place so the cleanup is non-destructive and can be
    reversed if either module is restored later.
    """
    cr.execute(
        """
        UPDATE ir_ui_view AS target_view
           SET active = FALSE,
               write_uid = 1,
               write_date = NOW()
          FROM ir_model_data AS data
         WHERE data.model = 'ir.ui.view'
           AND data.res_id = target_view.id
           AND data.module IN ('thamar_fabric_weight', 'thamar_mrp_custom')
           AND target_view.active IS TRUE
        RETURNING target_view.id
        """
    )
    disabled_view_ids = [row[0] for row in cr.fetchall()]
    _logger.info(
        "Disabled %s orphaned legacy product views: %s",
        len(disabled_view_ids),
        disabled_view_ids,
    )
