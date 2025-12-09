# Shop Floor Timer Enhancement

## Overview
Enhanced the shop floor timer display to show time in a more comprehensive format including days, hours, minutes, and seconds instead of just minutes and seconds.

## Changes Made

### File Modified
- `addons/mrp/static/src/widgets/timer.js`

### Function Updated
- `formatMinutes(value)` - The timer formatting function

## New Format

### Before
- Format: `MM:SS` (minutes:seconds)
- Example: `125:30` (125 minutes and 30 seconds)

### After
- Format: `Dd HH:MM:SS` (days, hours:minutes:seconds)
- Examples:
  - `00:05:30` (5 minutes and 30 seconds)
  - `02:15:45` (2 hours, 15 minutes, and 45 seconds)
  - `1d 05:30:20` (1 day, 5 hours, 30 minutes, and 20 seconds)

## Display Logic

1. **Days**: Only shown when >= 1 day (e.g., `1d`, `2d`)
2. **Hours**: Shown when >= 1 hour OR when days are present (always 2 digits with leading zero)
3. **Minutes**: Always shown (2 digits with leading zero)
4. **Seconds**: Always shown (2 digits with leading zero)

## Technical Details

The function converts the input value (in minutes) to total seconds, then calculates:
- Days: `totalSeconds / 86400`
- Hours: `(totalSeconds % 86400) / 3600`
- Minutes: `(totalSeconds % 3600) / 60`
- Seconds: `totalSeconds % 60`

## Impact

This change affects:
- Shop floor timer display in work orders
- Manufacturing order duration display
- Any component using the `mrp_timer` widget or `formatMinutes` formatter

## Testing Recommendations

1. Start a work order and verify the timer displays correctly
2. Test with operations running for:
   - Less than 1 hour (should show MM:SS)
   - More than 1 hour (should show HH:MM:SS)
   - More than 1 day (should show Dd HH:MM:SS)
3. Verify negative values display correctly with the minus sign

## Compatibility
- Odoo Version: 19.0
- Module: `mrp` (Manufacturing)

