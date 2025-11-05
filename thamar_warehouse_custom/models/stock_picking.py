from odoo import models, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """
        Override validation to ensure only warehouse managers can validate pickings.
        Keepers can create and edit, but only managers can validate.
        """
        user = self.env.user

        # Skip check if user is admin or has stock manager rights
        if user.has_group('stock.group_stock_manager') or user._is_admin():
            return super().button_validate()

        # Check if user is in warehouse keeper/manager groups
        if user.has_group('thamar_warehouse_custom.group_warehouse_keeper'):
            for picking in self:
                warehouse = picking.picking_type_id.warehouse_id

                # If no warehouse is set, allow validation (internal transfers, etc.)
                if not warehouse:
                    continue

                # Check if user is the manager of this warehouse
                if warehouse.manager_id and warehouse.manager_id != user:
                    raise UserError(
                        "Only the warehouse manager (%s) can validate pickings for warehouse '%s'.\n"
                        "You are assigned as keeper, not manager." % (
                            warehouse.manager_id.name,
                            warehouse.name
                        )
                    )

                # If no manager is assigned, check if user is at least a keeper
                if not warehouse.manager_id and warehouse.keeper_id != user:
                    raise UserError(
                        "You are not authorized to validate pickings for warehouse '%s'." % warehouse.name
                    )

        return super().button_validate()
