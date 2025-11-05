# Quick Start Guide - Thamar Product Barcode Generator

## 🚀 Installation (5 minutes)

### Step 1: Install the Module

**Option A: From UI**
1. Go to **Apps**
2. Click **Update Apps List**
3. Search for "Thamar Product Barcode"
4. Click **Install**

**Option B: From Command Line**
```bash
cd /home/mohsen/Documents/thmar-dani/odoo19
./odoo-bin -i thamar_product_barcode -d your_database_name --stop-after-init
```

---

## ⚙️ Configuration (10 minutes)

### Step 2: Set Category Codes

1. Go to **Inventory → Configuration → Product Categories**
2. Open "All" or create a new category
3. Set **Barcode Code**: `01`
4. Save

**Suggested Category Codes:**
```
Fabric      → 01
Clothing    → 02
Accessories → 03
Home Decor  → 04
```

### Step 3: Verify Attributes

The module automatically creates 4 attributes with sample values:
- ✅ Color (with codes: 0001-0006)
- ✅ Design (with codes: 0001-0005)
- ✅ Grade (with codes: 1-3)
- ✅ Type (with codes: P, D)

**To verify:**
1. Go to **Inventory → Configuration → Attributes**
2. Open each attribute
3. Check that values have **Barcode Code** filled

---

## 🎯 Create Your First Product (5 minutes)

### Step 4: Create Product with Variants

1. Go to **Inventory → Products → Products**
2. Click **Create**

**Fill in:**
- **Product Name**: "Cotton Fabric"
- **Category**: Select a category with barcode code (e.g., "Fabric - 01")
- **Can be Sold**: ✓
- **Auto Generate Barcode**: ✓ (should be checked by default)

3. Go to **Attributes & Variants** tab
4. Click **Add a line** and add:
   - **Attribute**: Color → **Values**: Red, Blue
   - **Attribute**: Design → **Values**: Plain, Striped
   - **Attribute**: Grade → **Values**: Grade 1, Grade 2
   - **Attribute**: Type → **Values**: Printing, Drying

5. Click **Generate Variants**

**Result**: 16 variants will be created (2×2×2×2)

### Step 5: View Generated Barcodes

1. Stay on the product form
2. Click **Variants** tab
3. See the **Barcode** column

**Example Barcodes:**
```
01000100011P  → Red, Plain, Grade 1, Printing
01000100011D  → Red, Plain, Grade 1, Drying
01000100021P  → Red, Plain, Grade 2, Printing
01000200011P  → Red, Striped, Grade 1, Printing
01000200021D  → Red, Striped, Grade 2, Drying
```

---

## 🔍 Understanding the Barcode

### Barcode Breakdown

Take barcode: `01000100011P`

```
01  0001  0001  1  P
│    │     │    │  │
│    │     │    │  └─ Type: P (Printing)
│    │     │    └──── Grade: 1 (Premium)
│    │     └───────── Design: 0001 (Plain)
│    └─────────────── Color: 0001 (Red)
└──────────────────── Category: 01 (Fabric)
```

**Total Length**: 12 characters

---

## 🛠️ Common Tasks

### Add New Color

1. **Inventory → Configuration → Attributes**
2. Open "Color"
3. Click **Add a line**
4. **Name**: "Orange"
5. **Barcode Code**: `0007`
6. Save

### Add New Design

1. **Inventory → Configuration → Attributes**
2. Open "Design"
3. Click **Add a line**
4. **Name**: "Checkered"
5. **Barcode Code**: `0006`
6. Save

### Regenerate Barcode

If you change attribute codes:
1. Open the product variant
2. Click **Regenerate Barcode** button
3. Check **Barcode Generation Log**

### Disable Auto-Generation

For specific products:
1. Open product template
2. Uncheck **Auto Generate Barcode**
3. Manually set barcode

---

## 📊 Testing Checklist

- [ ] Module installed successfully
- [ ] Category has barcode code (2 digits)
- [ ] All attribute values have barcode codes
- [ ] Created product with 4 attributes
- [ ] Variants generated successfully
- [ ] Barcodes appear in Variants tab
- [ ] Barcode has 12 characters
- [ ] Barcode follows structure: CCCCCCDDDDGT

---

## ⚠️ Troubleshooting

### Problem: Barcode is empty

**Check:**
1. Is "Auto Generate Barcode" enabled?
2. Does category have barcode code?
3. Do all 4 attributes have values with codes?

**Solution:**
- Open product variant
- Click "Regenerate Barcode"
- Check "Barcode Generation Log" for errors

### Problem: "Missing barcode codes" error

**Error Message:**
```
ERROR: Missing barcode codes for: color, design
```

**Solution:**
1. Go to **Inventory → Configuration → Attributes**
2. Open the missing attribute (e.g., Color)
3. For each value, set **Barcode Code**
4. Regenerate barcode

### Problem: "Invalid field 'barcode_position'" error

**This means:**
- The attribute model doesn't have the field yet
- Module not fully installed

**Solution:**
1. Restart Odoo server
2. Upgrade the module:
   ```bash
   ./odoo-bin -u thamar_product_barcode -d your_database --stop-after-init
   ```

---

## 📝 Code Reference

### Category Codes (2 digits)
```
01-99  → Numeric only
Example: 01, 02, 03
```

### Color Codes (4 digits)
```
0001-9999  → Numeric only
Example: 0001 (Red), 0002 (Blue)
```

### Design Codes (4 digits)
```
0001-9999  → Numeric only
Example: 0001 (Plain), 0002 (Striped)
```

### Grade Codes (1 digit)
```
1-9  → Numeric only
Example: 1 (Premium), 2 (Standard), 3 (Economy)
```

### Type Codes (1 letter)
```
A-Z  → Letter only
Example: P (Printing), D (Drying), E (Embroidery)
```

---

## 🎓 Best Practices

### 1. Plan Your Coding Scheme

Before creating products, plan:
- Category codes (01-99)
- Color code ranges (0001-0999 for primary, 1000-1999 for secondary)
- Design code ranges
- Grade levels
- Type codes

### 2. Document Your Codes

Create a spreadsheet:
```
Category | Code | Description
---------|------|------------
Fabric   | 01   | All fabric products
Clothing | 02   | Finished garments
...

Color    | Code | Hex
---------|------|-----
Red      | 0001 | #FF0000
Blue     | 0002 | #0000FF
...
```

### 3. Use Sequential Numbers

- Start from 0001, 0002, 0003...
- Easier to manage and remember
- Leaves room for expansion

### 4. Reserve Ranges

- Colors 0001-0999: Standard colors
- Colors 1000-1999: Custom colors
- Colors 2000-2999: Seasonal colors

### 5. Test Before Mass Creation

- Create 1-2 test products first
- Verify barcodes are correct
- Then create remaining products

---

## 📞 Support

If you encounter issues:
1. Check the **Barcode Generation Log** on product variant
2. Verify all codes are set correctly
3. Check Odoo logs: `tail -f /var/log/odoo/odoo.log`
4. Contact your Odoo administrator

---

## 🎉 Success!

You now have automatic barcode generation working!

**Next Steps:**
1. Add more colors, designs, grades, types
2. Create more product categories with codes
3. Create products with variants
4. Print barcode labels
5. Use barcodes in inventory operations

---

## 📚 Additional Resources

- Full documentation: See `README.md`
- Module structure: See `__manifest__.py`
- Code examples: See `models/` directory

**Happy Barcoding! 🏷️**

