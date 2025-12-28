# Migration Guide: Merging Payment Approval into Invoice Module

## Overview

The payment approval functionality has been **merged** from `thamar_account_payment_approval` into `thamar_invoice_custom`.

## What Changed

### ✅ **Merged Into One Module**
- **Before**: 2 separate modules
  - `thamar_account_payment_approval` (approval workflow)
  - `thamar_invoice_custom` (cheque fields, reports, Arabic amounts)
- **After**: 1 unified module
  - `thamar_invoice_custom` (everything combined)

### ✅ **Simplified Security Groups**
- **Before**: 2 groups
  - `group_payment_confirm` (for Confirm button)
  - `group_payment_validate` (for Validate button)
- **After**: 1 group
  - `group_payment_approval` (for Approve/Reject buttons)

### ✅ **What Stays the Same**
- ✅ All reports unchanged
- ✅ Cheque fields unchanged
- ✅ Arabic amount conversion unchanged
- ✅ Approval workflow works the same way

## Migration Steps

### Step 1: Uninstall Old Approval Module

```bash
# From Odoo UI:
# 1. Go to Apps
# 2. Remove "Apps" filter
# 3. Search "Thamar Payment Approval"
# 4. Click Uninstall
```

**OR** from command line:
```bash
cd /home/mohsen/Documents/thmar-dani/odoo19
./odoo-bin -d YOUR_DATABASE -u thamar_invoice_custom --uninstall thamar_account_payment_approval
```

### Step 2: Upgrade Invoice Module

```bash
# From Odoo UI:
# 1. Go to Apps
# 2. Remove "Apps" filter
# 3. Search "Thamar Invoice Customization"
# 4. Click Upgrade
# 5. Refresh browser (Ctrl+F5)
```

**OR** from command line:
```bash
cd /home/mohsen/Documents/thmar-dani/odoo19
./odoo-bin -d YOUR_DATABASE -u thamar_invoice_custom
```

### Step 3: Update User Groups

1. Go to **Settings > Users & Companies > Groups**
2. Search for "**Payment Approver**"
3. Add users who should be able to approve payments
4. Remove old groups if they exist:
   - "Payment Confirmer" (old)
   - "Payment Validator" (old)

### Step 4: Test the Workflow

1. Create a new payment
2. Verify [Approve] button appears (only for users in "Payment Approver" group)
3. Click [Approve]
4. Click [Confirm]
5. Verify payment is posted

## Module Comparison

| Feature | Old (Separate) | New (Merged) |
|---------|----------------|--------------|
| **Approval Fields** | thamar_account_payment_approval | thamar_invoice_custom |
| **Cheque Fields** | thamar_invoice_custom | thamar_invoice_custom |
| **Reports** | thamar_invoice_custom | thamar_invoice_custom ✅ |
| **Arabic Amounts** | thamar_invoice_custom | thamar_invoice_custom ✅ |
| **Security Groups** | 2 groups | 1 group |
| **Total Modules** | 2 | 1 ✅ |

## New Security Group

### `group_payment_approval`
- **Name**: Payment Approver
- **Category**: Accounting
- **Purpose**: Users can approve/reject payments
- **Buttons Controlled**:
  - [Approve] button
  - [Reject Approval] button

## Files Changed

### `thamar_invoice_custom/models/account_payment.py`
- ✅ Added approval fields (`is_approved`, `approved_by`, `approved_date`)
- ✅ Added `action_approve_payment()` method
- ✅ Added `action_reject_approval()` method
- ✅ Overridden `action_post()` to check approval
- ✅ Overridden `action_draft()` to reset approval

### `thamar_invoice_custom/views/account_payment_view.xml`
- ✅ Added [Approve] button with group restriction
- ✅ Added [Reject Approval] button with group restriction
- ✅ Added approval banners (green when approved, yellow when not)
- ✅ Added approval column in tree view
- ✅ Kept all cheque fields

### `thamar_invoice_custom/security/payment_security.xml`
- ✅ Replaced 2 groups with 1 `group_payment_approval`

### `thamar_invoice_custom/__manifest__.py`
- ✅ Updated version to 19.0.2.0.0
- ✅ Updated summary to include approval

## Benefits

1. ✅ **Simpler**: One module instead of two
2. ✅ **Cleaner**: One security group instead of two
3. ✅ **Easier to maintain**: All payment customizations in one place
4. ✅ **No conflicts**: No view inheritance priority issues
5. ✅ **Better organization**: Related features together

## Troubleshooting

### Issue: Approve button not visible
**Solution**: Make sure user is in "Payment Approver" group

### Issue: Old groups still exist
**Solution**: 
1. Go to Settings > Technical > Security > Groups
2. Search for "Payment Confirmer" and "Payment Validator"
3. Delete them manually

### Issue: Module upgrade fails
**Solution**:
1. Uninstall `thamar_account_payment_approval` first
2. Then upgrade `thamar_invoice_custom`

## Next Steps

After migration:
1. ✅ Delete the `thamar_account_payment_approval` folder (optional)
2. ✅ Test all payment workflows
3. ✅ Verify reports still work
4. ✅ Verify Arabic amounts still work
5. ✅ Verify cheque fields still work

