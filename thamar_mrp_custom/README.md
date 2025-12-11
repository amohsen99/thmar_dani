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

### 3. Features Tab on Manufacturing Orders
A new "Features" tab has been added to Manufacturing Orders with the following fields:

**Product Specifications:**
- **Color**: Many2one field to select from configured colors
- **Design**: Many2one field to select from configured designs
- **Width**: Float field for product width
- **Weight**: Float field for product weight

**Calculations:**
- **Density**: Float field for product density
- **Average**: Computed field calculated as `(1000/(width/weight))*100`

**Design Preview:**
- When a design is selected, its image is displayed in a preview section (400x400 pixels)

### 4. Configuration Menus

**Colors Configuration** (Manufacturing > Configuration > Colors):
- **Color Name**: Required field
- **Color Code**: Optional code (e.g., hex code or reference)
- **Customer**: Link to a customer
- **Notes**: Additional notes about the color

**Designs Configuration** (Manufacturing > Configuration > Designs):
- **Design Name**: Required field
- **Design Image**: Upload an image of the design
- Images are displayed in both the list view (64x64) and form view (200x200)

## Installation

1. Copy the module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "Thamar MRP Custom" module

## Dependencies
- `mrp` - Manufacturing module
- `sale` - Sales module

## Usage

### Setting up Colors and Designs
1. Navigate to **Manufacturing > Configuration > Colors**
2. Create color records with name, code, customer, and notes
3. Navigate to **Manufacturing > Configuration > Designs**
4. Create design records with name and upload images

### Using Features in Manufacturing Orders
When creating or editing a Manufacturing Order:
1. Navigate to **Manufacturing > Operations > Manufacturing Orders**
2. Create or open a Manufacturing Order
3. In the form view header, you'll see:
   - **Customer**: Select the customer for this manufacturing order
   - **Sale Order**: Select the related sale order
4. Click on the **Features** tab to access:
   - Select a **Color** from the configured colors
   - Select a **Design** from the configured designs (image will appear below)
   - Enter **Width**, **Weight**, and **Density** values
   - The **Average** field will be automatically calculated based on width and weight

## Technical Details

### JavaScript Patches
- `static/src/widgets/timer.js`: Patches the `MrpTimer` and `MrpTimerField` components to use enhanced time formatting

### New Models Created
- `mrp.color`: Color configuration with name, code, customer, and notes
- `mrp.design`: Design configuration with name and image

### Models Extended
- `mrp.production`: Added `partner_id`, `sale_order_id`, `color_id`, `design_id`, `width`, `weight`, `density`, and `average` fields

### Views Created
- Color tree and form views with menu under Manufacturing > Configuration
- Design tree and form views with menu under Manufacturing > Configuration

### Views Modified
- Manufacturing Order form view:
  - Added `partner_id` and `sale_order_id` fields after the `user_id` field
  - Added "Features" tab with all feature fields and design preview

### Module Structure
```
thamar_mrp_custom/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── mrp_production.py      # Extended MO model
│   ├── mrp_color.py            # Color model
│   └── mrp_design.py           # Design model
├── security/
│   └── ir.model.access.csv     # Access rights
├── static/
│   └── src/
│       └── widgets/
│           └── timer.js        # Enhanced timer
└── views/
    ├── mrp_production_views.xml  # MO form with Features tab
    ├── mrp_color_views.xml       # Color views and menu
    └── mrp_design_views.xml      # Design views and menu
```

## Version
- Version: 19.0.1.0.0
- Compatible with: Odoo 19.0

