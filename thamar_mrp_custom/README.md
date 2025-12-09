# Thamar MRP Custom Module

## Overview
This module adds custom fields to Manufacturing Orders and enhances the shop floor timer display.

## Features

### 1. Enhanced Shop Floor Timer
The shop floor timer now displays time in a comprehensive format:
- **Format**: `Dd HH:MM:SS` (days, hours:minutes:seconds)
- **Examples**:
  - `00:05:30` - 5 minutes and 30 seconds
  - `02:15:45` - 2 hours, 15 minutes, and 45 seconds
  - `1d 05:30:20` - 1 day, 5 hours, 30 minutes, and 20 seconds

**Display Logic**:
- Days only shown when ≥ 1 day
- Hours shown when ≥ 1 hour or when days are present
- Minutes and seconds always shown with 2-digit padding

### 2. Additional Fields on Manufacturing Orders
- **Customer (partner_id)**: Link a customer/partner to the manufacturing order
- **Sale Order (sale_order_id)**: Link a sale order to the manufacturing order

These fields appear in the Manufacturing Order form view in the right column, after the "Responsible" field.

## Installation

1. Copy the module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "Thamar MRP Custom" module

## Dependencies
- `mrp` - Manufacturing module
- `sale` - Sales module

## Usage

When creating or editing a Manufacturing Order:
1. Navigate to Manufacturing > Operations > Manufacturing Orders
2. Create or open a Manufacturing Order
3. In the form view, you'll see two new fields:
   - **Customer**: Select the customer for this manufacturing order
   - **Sale Order**: Select the related sale order

Both fields are read-only when the MO is in 'Done' or 'Cancelled' state.

## Technical Details

### JavaScript Patches
- `static/src/widgets/timer.js`: Patches the `MrpTimer` and `MrpTimerField` components to use enhanced time formatting

### Models Extended
- `mrp.production`: Added `partner_id` and `sale_order_id` fields

### Views Modified
- Manufacturing Order form view: Added the new fields after the `user_id` field

### Module Structure
```
thamar_mrp_custom/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   └── mrp_production.py
├── static/
│   └── src/
│       └── widgets/
│           └── timer.js
└── views/
    └── mrp_production_views.xml
```

## Version
- Version: 19.0.1.0.0
- Compatible with: Odoo 19.0

