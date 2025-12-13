# Thamar MRP Workcenter Enhancements

## Overview

This module enhances the Manufacturing (MRP) module with two key features:
1. **Workcenter Quantity Tracking**: Display running and pending quantities in workcenters
2. **Work Order Sequence Dependencies**: Enforce sequential execution of work orders

## Features

### 1. Workcenter Quantity Tracking

The module adds two new computed fields to workcenters that are visible in multiple views:

#### Running Quantity (`qty_running`)
- Shows the total quantity currently being produced in the workcenter
- "Running" means the work order is in 'progress' state (timer has been started)
- Displayed with green decoration when > 0
- Helps identify which workcenters are actively producing

#### Pending Quantity (`qty_pending`)
- Shows the total quantity waiting in the workcenter but not yet started
- "Pending" means the work order is in 'ready' or 'blocked' state
- Displayed with orange/warning decoration when > 0
- Helps identify workload waiting to be processed

**Where to See:**
1. **Workcenter List View** (Manufacturing > Configuration > Work Centers)
   - Two new columns: "Running Quantity" and "Pending Quantity"

2. **Workcenter Overview Kanban Cards** (Manufacturing > Overview)
   - Running Qty: Shows with green text and play icon (▶️)
   - Pending Qty: Shows with orange text and clock icon (🕐)
   - Only visible when quantity > 0

**Use Case:**
- Quickly see which workcenters are busy and which have pending work
- Better capacity planning and resource allocation
- Identify bottlenecks in production
- Real-time production monitoring from overview dashboard

### 2. Work Order Sequence Dependencies

The module enforces sequential execution of work orders within a Manufacturing Order based on their sequence number.

#### How it Works:
- Work orders in a Manufacturing Order have a sequence number (e.g., 10, 20, 30)
- When a user tries to start a work order, the system checks if all previous work orders (with lower sequence numbers) are completed
- If any previous work order is not done, the system prevents starting and shows an error message listing the pending work orders

#### Example:
Manufacturing Order has 3 work orders:
- Work Order 1 (Sequence 10) - Cutting
- Work Order 2 (Sequence 20) - Assembly  
- Work Order 3 (Sequence 30) - Packaging

**Scenario:**
- User tries to start "Assembly" (sequence 20)
- If "Cutting" (sequence 10) is not done, system shows error:
  ```
  Cannot start work order "Assembly" (sequence 20).
  
  The following previous work orders must be completed first:
  Cutting
  ```

**Benefits:**
- Ensures correct production flow
- Prevents mistakes in manufacturing sequence
- Maintains quality control
- Enforces process discipline

## Installation

1. Copy the module to your Odoo addons directory: `thamar_dani/thamar_mrp_workcenter/`
2. Update the apps list in Odoo
3. Install the "Thamar MRP Workcenter Enhancements" module

## Usage

### Viewing Workcenter Quantities

**Option 1: List View**
1. Navigate to **Manufacturing > Configuration > Work Centers**
2. In the list view, you'll see two new columns:
   - **Running Quantity**: Quantity currently in progress (green when > 0)
   - **Pending Quantity**: Quantity waiting to start (orange when > 0)

**Option 2: Overview Kanban Cards**
1. Navigate to **Manufacturing > Overview**
2. Each workcenter card shows:
   - **Running Qty**: Green text with ▶️ icon (only when > 0)
   - **Pending Qty**: Orange text with 🕐 icon (only when > 0)
3. These appear below "In Progress" count and above "Late" count

**Note:** All fields update automatically as work orders change state

### Work Order Dependencies

1. Create a Manufacturing Order with multiple work orders
2. Work orders are automatically sequenced (10, 20, 30, etc.)
3. When starting a work order:
   - If it's the first work order (lowest sequence), it starts normally
   - If previous work orders are not done, an error message appears
   - Complete work orders in sequence order

## Technical Details

### Models Extended

- `mrp.workcenter`: Added `qty_running` and `qty_pending` computed fields
- `mrp.workorder`: Overridden `button_start()` method to add sequence validation

### Views Modified

- Workcenter list view: Added running and pending quantity columns
- Workcenter kanban view: Added running and pending quantity rows to cards

### Dependencies

- `mrp`: Manufacturing module (base Odoo)

## Module Structure

```
thamar_mrp_workcenter/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── mrp_workcenter.py    # Quantity tracking
│   └── mrp_workorder.py     # Sequence dependencies
└── views/
    └── mrp_workcenter_views.xml  # Workcenter list view
```

## Version

- **Version**: 19.0.1.0.0
- **Odoo Version**: 19.0
- **Author**: Thamar Dani

## Support

For issues or questions, please contact Thamar Dani.

