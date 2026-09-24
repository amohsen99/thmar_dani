# Odoo backups to FTP

Backups run directly on the Odoo Docker host `72.61.186.1`. The desktop and
Codex do not need to be running. Destination: `197.44.109.148`, directory
`/Odoo/odoo-backups`, account `odoo`.

The user explicitly requested **plain FTP in Active mode**, without TLS or
passive mode. This mode was verified by uploading and reading back a test
file from the Odoo host. Credentials are kept in the root-only (0600)
`/etc/odoo-backup-ftp.json` on that host, never in repository files.

## Schedule and operations

`odoo-backup-ftp.timer` runs at **00:00, 04:00, 08:00, 12:00, 16:00, 20:00**
in `Africa/Cairo`, including seasonal timezone changes. `Persistent=true`
causes one catch-up run after downtime; it does not replay every missed run.
The service cannot overlap itself; a filesystem lock also protects manual runs.

Run these commands on the Odoo host:

```bash
systemctl list-timers odoo-backup-ftp.timer
systemctl status odoo-backup-ftp.service
journalctl -u odoo-backup-ftp.service
systemctl start odoo-backup-ftp.service
```

The service uses `/usr/local/sbin/odoo-backup-ftp.py` (`backup_ftp.py` here)
and `/usr/local/sbin/odoo-backup-all.py` (`backup_all.py` here).

## Backup format and verification

Every run dynamically discovers all Odoo databases using
`list_dbs(force=True)`, ignoring selector filtering. PostgreSQL maintenance
and template databases are excluded because they are not Odoo databases.
Odoo's own `dump_db` produces one ZIP per database with `dump.sql`,
`manifest.json`, and the filestore. Odoo stays running, with the same live
backup consistency limitations as its database manager.

Private local copies are saved under `/var/backups/odoo/<UTC-run-timestamp>/`.
The same timestamp identifies the destination subfolder under
`/Odoo/odoo-backups`. Each ZIP is checked for CRC integrity, required restore
files, nonempty SQL, and SHA-256. Uploads use `.partial` names; the uploaded
file is read back and hashed before being renamed to its final name.
`backup-report.json` is uploaded alongside the ZIPs. Local `ftp-receipt.json`
records verification and completion time. These checks are not a restore test.

Failures remain on disk with a `.ftp-pending` marker and are retried on the
next run. The service returns failure when any upload is still pending;
inspect the journal for details. No external alerting or automatic retention
deletion is configured. Monitor free space on both servers.

To retry an existing run without making a new backup:

```bash
python3 /usr/local/sbin/odoo-backup-ftp.py --resume <UTC-run-timestamp>
```

## Previous Google Drive workflow

The Codex automation `daily-odoo-backups-to-google-drive` is **paused**, per
user confirmation. Previously uploaded Google Drive backups were not deleted.
The initial Drive run is documented in `upload-receipt-20260923.json`.
`run_backup.py` is the previous desktop download helper, not part of the new
server schedule. The prepared `backup_ftps.py` and `odoo-backup-ftps.*` files
are superseded and were never installed or enabled.

## First successful FTP run

Run `20260923T123257.166302Z` finished successfully on 23 September 2026 at
12:42:49 UTC. All eight Odoo databases (including the newly discovered
`HR-Live`) plus `backup-report.json` were uploaded to
`/Odoo/odoo-backups/20260923T123257.166302Z` and verified by SHA-256 readback.
The service exited successfully. ZIP files total 337,805,052 bytes.
