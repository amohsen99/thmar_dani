# Thamar Portal Attendance

Independent Odoo 19 addon depending only on `portal` and `hr_attendance`.

## Setup

Update the Apps list and install **Thamar Portal Attendance**. Link each portal
user to their employee using the employee's Related User field, in the user's
current company. Open `/my/home` and select **الحضور والانصراف**, or visit
`/my/attendance` directly.

## Behavior

- Read-only attendance history for the current user's employee/current company.
- Check-in, check-out, recorded worked hours (HH:MM), and open/closed status.
- Month/year filtering based on check-in (blank means all months) in the user's timezone (employee
  timezone, then UTC as fallbacks); 20 records per page, newest first.
- Open records display a dash for duration until check-out is recorded.
- No employee selector, attendance modification endpoints, or new portal ACLs.
  Elevated reads are constrained by the server-resolved employee identity.
- No employee link or no matching records produces an explanatory empty state.

The time-off module is optional. This addon adds a standard portal home card
without changing the existing time-off addon or its custom navigation.

## Tests

Run Odoo with `--test-enable --test-tags /thamar_portal_attendance` on a test
 database with this addon installed. HTTP tests cover identity tampering,
local month boundaries, invalid input, status filtering, home navigation,
pagination, open records, and unlinked/anonymous users.
