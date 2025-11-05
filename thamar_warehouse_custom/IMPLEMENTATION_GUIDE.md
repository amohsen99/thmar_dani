# Implementation Guide - Thamar Warehouse Custom Module

## What Was Fixed

### 1. **Security Groups** (`security/security.xml`)
**Before**: Groups had no category and no inheritance
**After**:
- Added `implied_ids` so groups inherit from stock.group_stock_user
- Manager group inherits from Keeper group (hierarchy)
- Removed `category_id` for compatibility with Odoo 19

### 2. **Record Rules** (`security/security.xml`)
**Before**: Only had rules for warehouse and picking
**After**: Added comprehensive record rules for:
- `stock.warehouse` - Users see only their assigned warehouses
- `stock.picking` - Users see only pickings from their warehouses
- `stock.move` - Users see only moves from their warehouses
- `stock.quant` - Users see only inventory in their warehouse locations
- `stock.location` - Users see only locations in their warehouses
- `stock.picking.type` - Users see only operation types from their warehouses
- `product.product` - Users can see all products (needed to create operations)
- `product.template` - Users can see all product templates

### 3. **Access Rights** (`security/ir.model.access.csv`)
**Before**: Only had access for warehouse model
**After**: Added access rights for all stock models:
- Keepers: Read, Write, Create (no Delete)
- Managers: Read, Write, Create (no Delete)
- Both can read products

### 4. **Validation Logic** (`models/stock_picking.py`)
**Before**: Simple check that failed in many cases
**After**: Improved logic that:
- Skips check for admin and stock managers
- Handles cases where warehouse is not set
- Provides clear error messages
- Allows managers to validate, blocks keepers

### 5. **Views** (`views/warehouse_views.xml`)
**Before**: Basic form view inheritance
**After**: 
- Added fields to form view with proper options
- Added fields to tree view (list view)
- Created "My Warehouses" menu item
- Added helpful empty state message

## Module Structure

```
thamar_warehouse_custom/
├── __init__.py                 # Module initialization
├── __manifest__.py             # Module metadata and dependencies
├── README.md                   # User documentation
├── IMPLEMENTATION_GUIDE.md     # This file
├── models/
│   ├── __init__.py            # Models initialization
│   ├── stock_warehouse.py     # Adds manager_id and keeper_id fields
│   ├── stock_picking.py       # Validation logic
│   ├── stock_move.py          # Placeholder for record rules
│   └── stock_quant.py         # Placeholder for record rules
├── security/
│   ├── security.xml           # Groups and record rules
│   └── ir.model.access.csv    # Access rights
└── views/
    └── warehouse_views.xml    # UI modifications
```

## How It Works

### Access Control Flow

1. **User Login** → Odoo checks user's groups
2. **User Opens Inventory** → Record rules filter data
3. **User Sees Only**:
   - Warehouses where `keeper_id = user` OR `manager_id = user`
   - Pickings where `picking_type_id.warehouse_id.keeper_id = user` OR `manager_id = user`
   - Moves, Quants, Locations following same pattern

### Validation Flow

1. **Keeper Creates Picking** → Allowed (has create permission)
2. **Keeper Clicks Validate** → `button_validate()` is called
3. **Method Checks**:
   - Is user admin? → Allow
   - Is user stock manager? → Allow
   - Is user in keeper/manager group? → Check warehouse assignment
   - Is user the warehouse manager? → Allow
   - Otherwise → **Raise Error**

## Installation Steps

### Step 1: Upgrade the Module

If the module is already installed:
```bash
# From Odoo directory
./odoo-bin -u thamar_warehouse_custom -d your_database_name
```

If installing for the first time:
```bash
# From Odoo directory
./odoo-bin -i thamar_warehouse_custom -d your_database_name
```

Or from the UI:
1. Go to Apps
2. Remove "Apps" filter
3. Search "Thamar Warehouse"
4. Click "Upgrade" or "Install"

### Step 2: Create Test Users

1. **Create Keeper User**:
   - Go to Settings → Users & Companies → Users
   - Click "Create"
   - Name: "Warehouse Keeper Test"
   - Login: "keeper_test"
   - Set password
   - Access Rights tab:
     - Thamar Warehouse: **Warehouse Keeper** ✓
   - Save

2. **Create Manager User**:
   - Go to Settings → Users & Companies → Users
   - Click "Create"
   - Name: "Warehouse Manager Test"
   - Login: "manager_test"
   - Set password
   - Access Rights tab:
     - Thamar Warehouse: **Warehouse Manager** ✓
   - Save

### Step 3: Assign Users to Warehouse

1. Go to Inventory → Configuration → Warehouses
2. Open your warehouse (e.g., "WH")
3. Set:
   - **Warehouse Manager**: Select "Warehouse Manager Test"
   - **Warehouse Keeper**: Select "Warehouse Keeper Test"
4. Save

### Step 4: Test as Keeper

1. Logout and login as "keeper_test"
2. Go to Inventory
3. You should see:
   - Only your assigned warehouse in "My Warehouses"
   - Only operations for your warehouse
4. Create a Receipt:
   - Inventory → Operations → Receipts
   - Create
   - Select products
   - Click "Validate" → **Should get error message**

### Step 5: Test as Manager

1. Logout and login as "manager_test"
2. Go to Inventory → Operations → Receipts
3. Open the receipt created by keeper
4. Click "Validate" → **Should succeed**

## Common Issues and Solutions

### Issue 1: Module Won't Install
**Error**: "Module not found"
**Solution**: 
- Check module is in addons path
- Restart Odoo server
- Update apps list

### Issue 2: Groups Not Showing
**Error**: Can't find "Warehouse Keeper" group
**Solution**:
- Make sure module is installed
- Check security.xml is loaded
- Restart Odoo in debug mode to see errors

### Issue 3: Users See All Warehouses
**Error**: Record rules not working
**Solution**:
- Check user doesn't have "Inventory / Administrator" group
- Check user has "Warehouse Keeper" or "Warehouse Manager" group
- Record rules only apply to these specific groups

### Issue 4: Validation Error for Everyone
**Error**: Even managers can't validate
**Solution**:
- Check manager is set on warehouse
- Check picking's operation type has warehouse set
- Check user has "Warehouse Manager" group (not just Keeper)

### Issue 5: Can't Create Pickings
**Error**: Access denied when creating
**Solution**:
- Check ir.model.access.csv has create permission (perm_create=1)
- Check user has Warehouse Keeper group
- Check user is assigned to at least one warehouse

## Testing Checklist

- [ ] Module installs without errors
- [ ] Groups appear in Settings → Users → Access Rights
- [ ] Warehouse form shows Manager and Keeper fields
- [ ] Warehouse list shows Manager and Keeper columns
- [ ] "My Warehouses" menu appears for keepers/managers
- [ ] Keeper can see only assigned warehouse
- [ ] Keeper can create pickings
- [ ] Keeper CANNOT validate pickings (gets error)
- [ ] Manager can validate pickings
- [ ] Keeper can see inventory (quants) for their warehouse
- [ ] Keeper CANNOT see other warehouses' data
- [ ] Admin can still see everything

## Next Steps / Enhancements

### Possible Improvements:

1. **Multiple Keepers per Warehouse**:
   - Change `keeper_id` to `keeper_ids` (Many2many)
   - Update record rules to use `in` instead of `=`

2. **Approval Workflow**:
   - Add "state" field to pickings
   - Keeper creates → "Draft"
   - Keeper submits → "Pending Approval"
   - Manager validates → "Done"

3. **Notifications**:
   - Send email to manager when keeper creates picking
   - Send email to keeper when manager validates

4. **Reports**:
   - Add report showing keeper's activities
   - Add report showing pending validations for manager

5. **Dashboard**:
   - Add dashboard for keepers showing their warehouse stats
   - Add dashboard for managers showing pending approvals

## Code Explanation

### Key Code Snippets

**Record Rule Domain**:
```python
['|', ('warehouse_id.keeper_id', '=', user.id), ('warehouse_id.manager_id', '=', user.id)]
```
This means: Show records where warehouse's keeper is current user OR warehouse's manager is current user

**Validation Check**:
```python
if warehouse.manager_id and warehouse.manager_id != user:
    raise UserError("Only the warehouse manager can validate...")
```
This means: If warehouse has a manager assigned AND current user is not that manager, raise error

**Group Inheritance**:
```xml
<field name="implied_ids" eval="[(4, ref('stock.group_stock_user'))]"/>
```
This means: When user gets this group, also give them stock_user group automatically

## Support

If you encounter issues:
1. Check Odoo logs: `tail -f /var/log/odoo/odoo.log`
2. Enable developer mode: Settings → Activate Developer Mode
3. Check record rules: Settings → Technical → Security → Record Rules
4. Check access rights: Settings → Technical → Security → Access Rights

## Conclusion

The module is now complete and ready for testing. All the business requirements are implemented:
- ✅ Keeper and Manager roles
- ✅ Per-warehouse assignment
- ✅ Restricted visibility (only see own warehouse)
- ✅ Validation control (only manager can validate)
- ✅ Proper security (record rules + access rights)
- ✅ User-friendly views and menus

Good luck with your implementation!

