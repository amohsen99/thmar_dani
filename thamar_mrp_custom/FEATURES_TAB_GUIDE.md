# Features Tab - Sale Order & Manufacturing Order Integration

## Overview

The Features tab has been added to **Sale Orders** with automatic synchronization to **Manufacturing Orders**. This allows you to specify product specifications at the sales stage and have them automatically transferred to production.

## Features Tab Fields

### Product Specifications
- **Finishing Type**: Printing or Drying
- **Color**: Select from configured colors
- **Design**: Select from configured designs with image preview

### Calculations
- **Width**: Product width (auto-calculated average)
- **Weight**: Product weight (auto-calculated average)
- **Density**: Product density
- **Average**: Auto-calculated as `(1000/(width/weight))*100`

## Workflow

```
┌─────────────────┐
│  Sale Order     │
│  (Draft)        │
│                 │
│  Features Tab:  │
│  - Color        │
│  - Design       │
│  - Width        │
│  - Weight       │
│  - etc.         │
└────────┬────────┘
         │
         │ Confirm Sale Order
         ↓
┌─────────────────┐
│ Manufacturing   │
│ Order Created   │
│                 │
│ Features Tab:   │
│ ✓ Auto-copied   │
│   from SO       │
└─────────────────┘
```

## How to Use

### 1. Add Features to Sale Order

1. Go to **Sales > Orders > Quotations**
2. Create or open a sale order
3. Go to **Features** tab
4. Fill in product specifications:
   - Select Finishing Type
   - Select Color
   - Select Design (image preview will appear)
   - Enter Width, Weight, Density
   - Average is calculated automatically

### 2. Confirm Sale Order

When you confirm the sale order:
- If the order creates manufacturing orders
- Features are **automatically copied** to all related MOs
- You'll see a success message in the Features tab

### 3. View Related Manufacturing Orders

- Click the **Manufacturing** smart button at the top
- Shows count of related MOs
- Click to view all related manufacturing orders

### 4. Features in Manufacturing Order

- Open any related manufacturing order
- Go to **Features** tab
- All specifications are already filled in from the sale order
- You can modify them if needed for production

## Smart Button

### Manufacturing Orders Smart Button
- **Location**: Top of Sale Order form
- **Shows**: Number of related manufacturing orders
- **Action**: Click to view all related MOs
- **Visibility**: Only visible when MOs exist

## Auto-Sync Behavior

### When Sale Order is Confirmed
✅ Features are copied to **all** related manufacturing orders

### When Manufacturing Order is Created
✅ Features are copied from the related sale order (if exists)

### Manual Sync
If you update features in the sale order after confirmation, you can manually sync:
1. Open the sale order
2. Update features in the Features tab
3. The system will sync to existing MOs

## Field Mapping

| Sale Order Field | Manufacturing Order Field |
|------------------|---------------------------|
| `finishing_type` | `finishing_type` |
| `color_id` | `color_id` |
| `design_id` | `design_id` |
| `width` | `width` |
| `weight` | `weight` |
| `density` | `density` |
| `average` | `average` (computed) |

## Examples

### Example 1: Custom Printed Product

**Sale Order - Features Tab:**
- Finishing Type: Printing
- Color: Red
- Design: Logo Design A
- Width: 100.00
- Weight: 50.00
- Density: 1.5
- Average: 500.00 (auto-calculated)

**Result:**
When confirmed, all manufacturing orders will have these exact specifications.

### Example 2: Multiple Manufacturing Orders

**Sale Order:**
- Product: Custom Box
- Quantity: 1000
- Features: Color=Blue, Design=Pattern B

**Manufacturing Orders Created:**
- MO/00001: 500 units → Features copied
- MO/00002: 500 units → Features copied

Both MOs have the same color and design specifications.

## Benefits

1. ✅ **Consistency**: Same specifications from sales to production
2. ✅ **Efficiency**: No manual re-entry of specifications
3. ✅ **Traceability**: Easy to track which SO created which MO
4. ✅ **Accuracy**: Reduces errors from manual data entry
5. ✅ **Visibility**: Smart button shows all related MOs

## Technical Details

### Models Extended
- `sale.order`: Added features fields and MO relation
- `mrp.production`: Enhanced with auto-sync from SO

### Methods Added

**Sale Order:**
- `_compute_average()`: Calculate average from width/weight
- `_compute_mrp_production_count()`: Count related MOs
- `action_view_mrp_production()`: Smart button action
- `_action_confirm()`: Override to sync features
- `_sync_features_to_mrp()`: Sync features to MOs

**Manufacturing Order:**
- `_sync_features_from_sale_order()`: Get features from SO
- `create()`: Override to auto-sync on creation

## Upgrade Instructions

```bash
cd /home/mohsen/Documents/thmar-dani/odoo19
./odoo-bin -u thamar_mrp_custom -d YOUR_DATABASE_NAME
```

Or from Odoo UI:
1. Go to Apps
2. Search "Thamar MRP Custom"
3. Click Upgrade
4. Refresh browser

