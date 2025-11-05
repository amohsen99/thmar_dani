# Thamar Warehouse Custom Access

## Overview
This module adds warehouse-specific user roles (Keeper and Manager) with restricted access to warehouse data. Each warehouse can have assigned keepers and managers who can only see and work with their assigned warehouse's data.

## Features

### 1. **Two User Roles**
- **Warehouse Keeper**: Can view and create stock operations for their assigned warehouse
- **Warehouse Manager**: Can validate stock operations (inherits Keeper permissions)

### 2. **Warehouse Assignment**
- Each warehouse can have:
  - One or more **Keepers** (assigned via `keeper_id` field)
  - One or more **Managers** (assigned via `manager_id` field)

### 3. **Access Control**
Users with Keeper/Manager roles can only see:
- Their assigned warehouses
- Stock pickings/transfers in their warehouses
- Stock moves in their warehouses
- Stock quants (inventory) in their warehouse locations
- Locations belonging to their warehouses
- Picking types (operation types) for their warehouses
- All products (needed to create operations)

### 4. **Validation Control**
- **Keepers** can create and edit stock operations but **cannot validate** them
- **Managers** can validate stock operations for their assigned warehouse
- Only the assigned manager can validate pickings for a specific warehouse

## Installation

1. Copy the module to your Odoo addons directory:
   ```
   /path/to/odoo/addons/thamar_dani/thamar_warehouse_custom/
   ```

2. Update the apps list:
   - Go to Apps menu
   - Click "Update Apps List"
   - Search for "Thamar Warehouse Custom Access"

3. Install the module:
   - Click "Install"

## Configuration

### Step 1: Assign Users to Groups

1. Go to **Settings → Users & Companies → Users**
2. Select a user
3. Go to the **Access Rights** tab
4. Under **Thamar Warehouse** section:
   - Check **Warehouse Keeper** for keepers
   - Check **Warehouse Manager** for managers

### Step 2: Assign Users to Warehouses

1. Go to **Inventory → Configuration → Warehouses**
2. Open a warehouse
3. Set the fields:
   - **Warehouse Manager**: Select the user who will manage this warehouse
   - **Warehouse Keeper**: Select the user who will keep/operate this warehouse

### Step 3: Test Access

1. Login as a Keeper user
2. Go to **Inventory → My Warehouses**
3. You should only see warehouses where you are assigned as keeper or manager
4. Try to create a transfer and validate it - you should get an error
5. Login as a Manager user
6. You should be able to validate the transfer

## Business Flow

### Typical Workflow:

1. **Keeper Creates Transfer**:
   - Keeper logs in
   - Goes to Inventory → Operations → Transfers
   - Creates a new receipt, delivery, or internal transfer
   - Fills in the products and quantities
   - Clicks "Validate" → **Gets Error** (only manager can validate)

2. **Manager Validates Transfer**:
   - Manager logs in
   - Goes to Inventory → Operations → Transfers
   - Opens the transfer created by keeper
   - Reviews the transfer
   - Clicks "Validate" → **Success**

3. **Inventory Visibility**:
   - Both Keeper and Manager can view inventory (stock quants) for their warehouse
   - They can see product quantities in their warehouse locations
   - They cannot see other warehouses' inventory

## Technical Details

### Models Extended

1. **stock.warehouse**:
   - Added `manager_id` field (Many2one to res.users)
   - Added `keeper_id` field (Many2one to res.users)

2. **stock.picking**:
   - Override `button_validate()` method to check if user is the warehouse manager

3. **stock.move**: Access controlled via record rules

4. **stock.quant**: Access controlled via record rules

### Security

#### Groups:
- `group_warehouse_keeper`: Inherits from `stock.group_stock_user`
- `group_warehouse_manager`: Inherits from `group_warehouse_keeper`

#### Record Rules:
All record rules filter data based on:
```python
['|', ('warehouse_id.keeper_id', '=', user.id), ('warehouse_id.manager_id', '=', user.id)]
```

This ensures users only see records for warehouses where they are assigned.

#### Access Rights (ir.model.access.csv):
- Keepers: Read + Write + Create (no Delete)
- Managers: Read + Write + Create (no Delete)
- Both can see all products (needed for operations)

### Views

1. **Warehouse Form View**: Shows Manager and Keeper fields
2. **Warehouse Tree View**: Shows Manager and Keeper columns
3. **My Warehouses Menu**: Quick access to assigned warehouses

## Troubleshooting

### Issue: User can't see any warehouses
**Solution**: Make sure the user is assigned to a warehouse as either keeper or manager

### Issue: User can't create transfers
**Solution**: 
1. Check if user has "Warehouse Keeper" group
2. Check if user is assigned to the warehouse
3. Check if the picking type belongs to their warehouse

### Issue: Manager can't validate transfers
**Solution**:
1. Verify the user is set as `manager_id` on the warehouse
2. Check that the picking's operation type belongs to that warehouse
3. Make sure the user has "Warehouse Manager" group

### Issue: User sees all warehouses
**Solution**: 
1. Check if user has "Inventory / Administrator" or "Inventory / Manager" groups
2. These groups bypass the custom restrictions
3. Remove those groups and assign only "Warehouse Keeper" or "Warehouse Manager"

## Customization

### To add more restricted models:

1. Add record rule in `security/security.xml`:
```xml
<record id="rule_model_name_keeper_see_own" model="ir.rule">
    <field name="name">Warehouse Keeper: See Own Records</field>
    <field name="model_id" ref="module.model_name"/>
    <field name="domain_force">['|', ('warehouse_id.keeper_id', '=', user.id), ('warehouse_id.manager_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('group_warehouse_keeper'))]"/>
</record>
```

2. Add access rights in `security/ir.model.access.csv`:
```csv
access_model_keeper,model_keeper_access,module.model_name,group_warehouse_keeper,1,1,1,0
access_model_manager,model_manager_access,module.model_name,group_warehouse_manager,1,1,1,0
```

## Support

For issues or questions, contact the module author or your Odoo administrator.

## License

LGPL-3

## Author

Generated for Mohsen

