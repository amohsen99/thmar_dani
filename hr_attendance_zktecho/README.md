# Continuous ZKTeco attendance

Upgrade `hr_attendance_zktecho` to install these Odoo scheduled actions:

- **ZKTeco: Download Device Attendances** — every two hours.
- **ZKTeco: Move Drafts to HR Attendances** — every two hours, up to 1,000 punches per run.

Intervals can be changed under Settings → Technical → Scheduled Actions.
Both jobs run all day, including weekends. The existing attendance routing,
anti-duplicate window and maximum shift duration settings remain in effect.
Choose a maximum duration longer than the longest legitimate employee shift.

Downloads read the logs without disabling the device or clearing its punches.
The initial automatic download reads all retained device history; later runs
resume from the last successful download with two days of overlap. Manual date
filters do not limit automatic downloads. Device timestamps are converted to UTC
before applying the download range.

Only enable **Automatic Attendance Sync** on devices that should participate.
Each device shows its last successful automatic download and most recent error.
An offline device is retried next run; it does not roll back successful downloads
from other devices. Draft movement waits for all enabled devices to have synced,
then processes through the earliest successful download minus two minutes. This
prevents an OUT device getting ahead of an unavailable IN device. If a device is
permanently retired, disable its Automatic Attendance Sync setting.

Check-ins stay open across cron runs and midnight. A subsequent checkout closes
the same attendance, subject to the configured maximum shift duration. Duplicate
suppression also considers the last linked punch from a previous run. Unexpected
late punches older than already moved attendance are left for manual review;
failures are logged with the employee ID and retried, without saving partial
changes for that employee. Manual downloads, manual moves and scheduled jobs use
a shared database lock to prevent overlapping imports.

As in the manual move wizard, automatic moves skip work-entry generation. Use
the existing Generate Work Entries action when required.

Regression tests: run Odoo with `--test-enable --test-tags /hr_attendance_zktecho`
on an isolated database. Tests mock device connections and cover all three shift
periods/routing modes, overnight continuation, repeated runs, UTC boundaries,
duplicates, offline devices, transaction rollback and concurrency protection.
