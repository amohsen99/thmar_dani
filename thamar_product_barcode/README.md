# Thamar Product Barcode Generator

## Overview
This module automatically generates barcodes for product variants based on category codes and product attributes (Color, Design, Grade, Type).

## Barcode Structure

The barcode is composed of 12 characters:

```
[CC][CCCC][DDDD][G][T]
 │    │      │    │  │
 │    │      │    │  └─ Type (1 char): P=Printing, D=Drying
 │    │      │    └──── Grade (1 char): 1, 2, 3
 │    │      └───────── Design (4 chars): 0001-9999
 │    └──────────────── Color (4 chars): 0001-9999
 └───────────────────── Category (2 chars): 01-99
```

**Example**: `01000100011P`
- Category: `01`
- Color: `0001` (Red)
- Design: `0001` (Plain)
- Grade: `1` (Premium)
- Type: `P` (Printing)

## Features

### 1. **Category Barcode Codes**
- Add 2-digit codes to product categories
- Codes must be unique and numeric (01-99)
- Used as the first 2 characters of the barcode

### 2. **Attribute Barcode Codes**
- **Color**: 4-digit code (0001-9999)
- **Design**: 4-digit code (0001-9999)
- **Grade**: 1-digit code (1-9)
- **Type**: 1-letter code (P, D, etc.)

### 3. **Automatic Barcode Generation**
- Barcodes are generated automatically when:
  - A new product variant is created
  - Variant attributes are changed
  - Product category is changed
- Can be disabled per product template

### 4. **Manual Regeneration**
- Button to manually regenerate barcode
- Useful after updating attribute codes

### 5. **Generation Log**
- Detailed log of barcode generation process
- Shows which codes were used
- Displays errors if codes are missing

### 6. **Validation**
- Ensures all codes have correct length
- Prevents duplicate codes within same attribute
- Checks for duplicate barcodes

## Installation

1. Copy the module to your Odoo addons directory
2. Update the apps list
3. Install "Thamar Product Barcode Generator"

## Configuration

### Step 1: Set Category Codes

1. Go to **Inventory → Configuration → Product Categories**
2. Open a category
3. Set **Barcode Code** (2 digits, e.g., "01")
4. Save

**Example Categories:**
- Fabric: `01`
- Clothing: `02`
- Accessories: `03`

### Step 2: Configure Attributes

The module creates 4 attributes automatically:
- Color
- Design
- Grade
- Type

#### Set Attribute Codes:

1. Go to **Inventory → Configuration → Attributes**
2. Open an attribute (e.g., "Color")
3. For each value, set the **Barcode Code**:

**Color Codes (4 digits):**
- Red: `0001`
- Blue: `0002`
- Green: `0003`
- Yellow: `0004`
- Black: `0005`
- White: `0006`

**Design Codes (4 digits):**
- Plain: `0001`
- Striped: `0002`
- Dotted: `0003`
- Floral: `0004`
- Geometric: `0005`

**Grade Codes (1 digit):**
- Grade 1 (Premium): `1`
- Grade 2 (Standard): `2`
- Grade 3 (Economy): `3`

**Type Codes (1 letter):**
- Printing: `P`
- Drying: `D`

### Step 3: Create Products with Variants

1. Go to **Inventory → Products → Products**
2. Create a new product
3. Set the **Category** (must have barcode code)
4. Enable **Auto Generate Barcode** (enabled by default)
5. Go to **Attributes & Variants** tab
6. Add the 4 attributes:
   - Color
   - Design
   - Grade
   - Type
7. Select values for each attribute
8. Click **Generate Variants**

The barcode will be automatically generated for each variant!

## Usage

### View Barcode Structure

On the product template form, you'll see:
- **Barcode Structure**: Preview of how barcode will be generated
- Example: `01[COLOR][DESIGN][GRADE][TYPE]`

### View Generated Barcodes

1. Go to product template
2. Click **Variants** tab
3. See the **Barcode** column for each variant

### Regenerate Barcode

If you change attribute codes:
1. Open the product variant
2. Click **Regenerate Barcode** button
3. Check the **Generation Log** for details

### View Generation Log

On each product variant:
- **Barcode Generation Log** field shows:
  - Which codes were used
  - Success/error messages
  - Barcode breakdown

## Examples

### Example 1: Red Plain Premium Printing Fabric

**Product**: Fabric
- Category: Fabric (`01`)
- Color: Red (`0001`)
- Design: Plain (`0001`)
- Grade: Premium (`1`)
- Type: Printing (`P`)

**Generated Barcode**: `01000100011P`

### Example 2: Blue Striped Standard Drying Clothing

**Product**: Clothing
- Category: Clothing (`02`)
- Color: Blue (`0002`)
- Design: Striped (`0002`)
- Grade: Standard (`2`)
- Type: Drying (`D`)

**Generated Barcode**: `02000200022D`

## Troubleshooting

### Barcode Not Generated

**Check:**
1. Is "Auto Generate Barcode" enabled?
2. Does the category have a barcode code?
3. Do all attribute values have barcode codes?
4. Check the "Barcode Generation Log" for errors

### Missing Codes Error

**Error**: "Missing barcode codes for: color, design"

**Solution**: 
1. Go to Inventory → Configuration → Attributes
2. Open the attribute (Color, Design, etc.)
3. Set barcode codes for all values

### Duplicate Barcode Warning

**Warning**: "Barcode already exists for product X"

**Solution**:
- This means two variants have the same combination
- Check if you have duplicate variant combinations
- Or manually adjust one of the barcodes

### Invalid Code Length

**Error**: "Color code must be exactly 4 characters"

**Solution**:
- Color codes: Must be 4 digits (e.g., `0001`)
- Design codes: Must be 4 digits (e.g., `0001`)
- Grade codes: Must be 1 digit (e.g., `1`)
- Type codes: Must be 1 letter (e.g., `P`)

## Technical Details

### Models Extended

1. **product.category**
   - Added `barcode_code` field (2 chars)

2. **product.attribute**
   - Added `barcode_position` field (color/design/grade/type)

3. **product.attribute.value**
   - Added `barcode_code` field

4. **product.template**
   - Added `auto_generate_barcode` field
   - Added `barcode_preview` computed field

5. **product.product**
   - Added `barcode_generation_log` field
   - Override `create()` and `write()` methods
   - Added `_generate_barcode()` method
   - Added `action_regenerate_barcode()` action

### Barcode Generation Logic

```python
barcode = category_code + color_code + design_code + grade_code + type_code
# Example: "01" + "0001" + "0001" + "1" + "P" = "01000100011P"
```

### Validation Rules

- Category codes: 2 digits, unique
- Color codes: 4 digits, unique per attribute
- Design codes: 4 digits, unique per attribute
- Grade codes: 1 digit, unique per attribute
- Type codes: 1 letter, unique per attribute

## Adding More Values

### Add New Color

1. Go to Inventory → Configuration → Attributes
2. Open "Color" attribute
3. Click "Add a line" in Values
4. Name: "Orange"
5. Barcode Code: `0007`
6. Save

### Add New Type

1. Go to Inventory → Configuration → Attributes
2. Open "Type" attribute
3. Click "Add a line" in Values
4. Name: "Embroidery"
5. Barcode Code: `E`
6. Save

## Best Practices

1. **Plan Your Codes**: Create a coding scheme before starting
2. **Document Codes**: Keep a list of all codes and their meanings
3. **Sequential Numbering**: Use sequential numbers for easier management
4. **Reserve Ranges**: Reserve code ranges for future expansion
5. **Test First**: Test with a few products before mass creation

## Support

For issues or questions, contact your Odoo administrator.

## License

LGPL-3

## Author

Thamar Dani

