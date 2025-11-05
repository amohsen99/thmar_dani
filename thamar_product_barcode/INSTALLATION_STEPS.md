# Installation Steps - Thamar Product Barcode

## Step 1: Upgrade the Module

```bash
cd /home/mohsen/Documents/thmar-dani/odoo19
./odoo-bin -u thamar_product_barcode -d your_database_name --stop-after-init
```

Or from UI:
1. Go to Apps
2. Search "Thamar Product Barcode"
3. Click "Upgrade"

## Step 2: Verify Installation

### Check Category Field
1. Go to **Inventory → Configuration → Product Categories**
2. Open "All" category
3. You should see **Barcode Code** field
4. Enter: `01`
5. Save

### Check Attributes
1. Go to **Inventory → Configuration → Attributes**
2. You should see 4 attributes:
   - Color
   - Design
   - Grade
   - Type

3. Open "Color" attribute
4. You should see:
   - **Barcode Position** field (set to "Color (4 chars)")
   - Values with **Barcode Code** column:
     - Red: 0001
     - Blue: 0002
     - Green: 0003
     - etc.

## Step 3: Create Test Product

1. Go to **Inventory → Products → Products**
2. Click **Create**
3. Fill in:
   - **Product Name**: Test Fabric
   - **Category**: All (or any category with barcode code "01")
   - **Can be Sold**: ✓
   - **Auto Generate Barcode**: ✓ (should be checked)

4. You should see:
   - **Barcode Structure**: `01[COLOR][DESIGN][GRADE][TYPE]`

5. Go to **Attributes & Variants** tab
6. Add attributes:
   - Click "Add a line"
   - **Attribute**: Color
   - **Values**: Select "Red" and "Blue"
   
   - Click "Add a line"
   - **Attribute**: Design
   - **Values**: Select "Plain" and "Striped"
   
   - Click "Add a line"
   - **Attribute**: Grade
   - **Values**: Select "Grade 1 (Premium)"
   
   - Click "Add a line"
   - **Attribute**: Type
   - **Values**: Select "Printing"

7. Click **Generate Variants** (or save)

8. Go to **Variants** tab
9. You should see variants with barcodes:
   - Red, Plain, Grade 1, Printing: `01000100011P`
   - Red, Striped, Grade 1, Printing: `01000100021P`
   - Blue, Plain, Grade 1, Printing: `01000200011P`
   - Blue, Striped, Grade 1, Printing: `01000200021P`

## Step 4: Test Barcode Generation

1. Open one of the variants
2. You should see:
   - **Generate Barcode** button (with barcode icon)
   - **Barcode** field (should be filled)
   - **Barcode Generation Log** (shows generation details)

3. Click **Generate Barcode** button
4. Check the log - should show:
   ```
   === Barcode Generation for Test Fabric (Red, Plain, Grade 1, Printing) ===
   Category Code: 01
   Color Code: 0001 (Red)
   Design Code: 0001 (Plain)
   Grade Code: 1 (Grade 1 (Premium))
   Type Code: P (Printing)
   Generated Barcode: 01000100011P
   Structure: 01|0001|0001|1|P
   SUCCESS: Barcode updated
   ```

## Troubleshooting

### Issue: Fields not showing

**Solution**: Restart Odoo and upgrade module again
```bash
# Stop Odoo
# Then restart and upgrade
./odoo-bin -u thamar_product_barcode -d your_database_name
```

### Issue: Attributes not created

**Solution**: The data file has `noupdate="1"`, so it won't update existing data.

To force update:
```bash
./odoo-bin -u thamar_product_barcode -d your_database_name --init thamar_product_barcode
```

Or manually create attributes:
1. Go to Inventory → Configuration → Attributes
2. Create "Color" attribute
3. Set **Barcode Position**: Color (4 chars)
4. Add values with codes

### Issue: Barcode not generated

**Check**:
1. Is "Auto Generate Barcode" checked on product template?
2. Does category have barcode code?
3. Do all 4 attributes (Color, Design, Grade, Type) have values selected?
4. Do all attribute values have barcode codes?

**Solution**: Click "Generate Barcode" button on variant and check the log

### Issue: View errors

If you get view inheritance errors, check:
1. The parent view exists
2. The XPath expression is correct
3. Restart Odoo

## What You Should See

### On Product Category Form:
- [x] Barcode Code field (after Name)

### On Product Attribute Form:
- [x] Barcode Position field (after Display Type)
- [x] Barcode Code column in values tree

### On Product Template Form:
- [x] Auto Generate Barcode checkbox (before Barcode)
- [x] Barcode Structure field (after Barcode)

### On Product Variant Form:
- [x] Generate Barcode button (before Barcode)
- [x] Barcode field
- [x] Barcode Generation Log (after Barcode)

### On Product Template Variants Tab:
- [x] Barcode column in variants tree

## Next Steps

Once everything is working:
1. Set barcode codes for all your categories
2. Add more attribute values with codes
3. Create products with variants
4. Barcodes will be generated automatically!

## Support

If you still have issues:
1. Check Odoo logs: `tail -f /var/log/odoo/odoo.log`
2. Enable developer mode
3. Check Technical → Database Structure → Models
4. Verify fields exist on models

