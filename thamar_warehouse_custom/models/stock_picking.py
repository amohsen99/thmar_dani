from odoo import models, api, fields
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """
        Override validation to ensure only transfer validators can validate pickings.
        Keepers and managers can create and edit, but only validators can validate.
        """
        user = self.env.user

        # Skip check if user is admin or has stock manager rights
        if user.has_group('stock.group_stock_manager') or user._is_admin():
            return super().button_validate()

        # Check if user is a transfer validator (from settings)
        params = self.env['ir.config_parameter'].sudo()
        validator_ids_str = params.get_param('thamar_warehouse_custom.transfer_validator_ids', '[]')
        try:
            transfer_validator_ids = eval(validator_ids_str) if validator_ids_str else []
        except:
            transfer_validator_ids = []

        if user.id in transfer_validator_ids:
            return super().button_validate()

        # If user is in warehouse keeper/manager groups but not a validator, deny validation
        if user.has_group('thamar_warehouse_custom.group_warehouse_keeper'):
            raise UserError(
                "You are not authorized to validate transfers.\n"
                "Only Transfer Validators (configured in Inventory Settings) can validate transfers.\n"
                "Please contact your administrator."
            )

        return super().button_validate()

    def action_cancel(self):
        """
        Override cancel to ensure only managers or validators can cancel validated transfers.
        Keepers cannot cancel validated transfers.
        """
        user = self.env.user

        # Skip check if user is admin or has stock manager rights
        if user.has_group('stock.group_stock_manager') or user._is_admin():
            return super().action_cancel()

        # Check if user is a transfer validator (from settings)
        params = self.env['ir.config_parameter'].sudo()
        validator_ids_str = params.get_param('thamar_warehouse_custom.transfer_validator_ids', '[]')
        try:
            transfer_validator_ids = eval(validator_ids_str) if validator_ids_str else []
        except:
            transfer_validator_ids = []

        if user.id in transfer_validator_ids:
            return super().action_cancel()

        # Check if user is in warehouse groups
        if user.has_group('thamar_warehouse_custom.group_warehouse_keeper'):
            for picking in self:
                # If picking is validated (done), only managers or validators can cancel
                if picking.state == 'done':
                    warehouse = picking.picking_type_id.warehouse_id

                    # Check if user is a manager of this warehouse
                    if warehouse and warehouse.manager_ids and user in warehouse.manager_ids:
                        continue  # Manager can cancel

                    # Otherwise deny
                    raise UserError(
                        "You are not authorized to cancel validated transfers.\n"
                        "Only Warehouse Managers or Transfer Validators can cancel validated transfers.\n"
                        "Please contact your administrator."
                    )

        return super().action_cancel()
