# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    dyeing_menu_id = fields.Many2one(
        "ir.ui.menu",
        string="قائمة المخزن للطباعة والصباغة",
        ondelete="set null",
        copy=False,
        readonly=True,
    )
    dyeing_operations_action_id = fields.Many2one(
        "ir.actions.act_window",
        string="إجراء عمليات المخزن للطباعة والصباغة",
        ondelete="set null",
        copy=False,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        warehouses._sync_dyeing_warehouse_menus()
        return warehouses

    def write(self, values):
        result = super().write(values)
        if {"name", "code"} & set(values):
            self._sync_dyeing_warehouse_menus()
        return result

    def unlink(self):
        menus = self.mapped("dyeing_menu_id").exists()
        actions = self.mapped("dyeing_operations_action_id").exists()
        result = super().unlink()
        menus.sudo().unlink()
        actions.sudo().unlink()
        return result

    @api.model
    def _sync_dyeing_warehouse_menus(self):
        """Create one warehouse menu that opens Odoo's operations Kanban."""
        root_menu = self.env.ref(
            "thamar_printing_dyeing.menu_dyeing_material_issue",
            raise_if_not_found=False,
        )
        if not root_menu:
            return

        warehouses = self.sudo().with_context(active_test=False).search([])
        menu_groups = [(6, 0, root_menu.group_ids.ids)]
        for sequence, warehouse in enumerate(warehouses, start=1):
            domain = "[('warehouse_id', '=', %s), ('active', '=', True)]" % warehouse.id
            action_values = {
                "name": warehouse.name,
                "res_model": "stock.picking.type",
                "view_mode": "kanban,form",
                "domain": domain,
            }
            action = warehouse.dyeing_operations_action_id.sudo()
            if action:
                action.write(action_values)
            else:
                action = self.env["ir.actions.act_window"].sudo().create(action_values)
                warehouse.sudo().write({"dyeing_operations_action_id": action.id})

            menu_values = {
                "name": warehouse.name,
                "parent_id": root_menu.id,
                "action": "ir.actions.act_window,%s" % action.id,
                "sequence": sequence,
                "group_ids": menu_groups,
            }
            menu = warehouse.dyeing_menu_id.sudo()
            if menu:
                menu.write(menu_values)
            else:
                menu = self.env["ir.ui.menu"].sudo().create(menu_values)
                warehouse.sudo().write({"dyeing_menu_id": menu.id})
