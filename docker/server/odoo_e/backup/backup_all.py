#!/usr/bin/env python3
"""Run on the Docker host; export every Odoo database using Odoo's ZIP writer."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

os.umask(0o077)
root = Path('/var/backups/odoo')
root.mkdir(parents=True, exist_ok=True)
lock = (root / '.lock').open('w')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
bootstrap = "from odoo.tools import config; from odoo.service import db; config.parse_config(['-c','/etc/odoo/odoo.conf']); "
databases = json.loads(subprocess.check_output([
    'docker', 'exec', 'odoo', 'python3', '-c',
    bootstrap + 'import json; print(json.dumps(db.list_dbs(force=True)))',
], text=True))
if not databases:
    raise RuntimeError('No Odoo databases found')
run = root / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
run.mkdir()
report = {'run': str(run), 'databases': databases, 'files': [], 'errors': []}
for name in databases:
    try:
        if name in ('.', '..') or '/' in name or '\\' in name:
            raise ValueError('Database name is not safe for a filename')
        target = run / (name + '.zip')
        partial = target.with_suffix('.zip.partial')
        with partial.open('wb') as output:
            subprocess.run([
                'docker', 'exec', 'odoo', 'python3', '-c',
                bootstrap + "import sys; db.dump_db(sys.argv[1], sys.stdout.buffer, backup_format='zip', with_filestore=True)", name,
            ], stdout=output, check=True)
        with zipfile.ZipFile(partial) as archive:
            if archive.testzip() is not None:
                raise RuntimeError('ZIP integrity check failed')
            if not {'dump.sql', 'manifest.json'}.issubset(archive.namelist()):
                raise RuntimeError('Missing Odoo restore files')
            if archive.getinfo('dump.sql').file_size == 0:
                raise RuntimeError('Empty database dump')
            manifest = json.loads(archive.read('manifest.json'))
            filestore_files = sum(n.startswith('filestore/') and not n.endswith('/') for n in archive.namelist())
        partial.rename(target)
        digest = hashlib.sha256()
        with target.open('rb') as content:
            for chunk in iter(lambda: content.read(1024 * 1024), b''):
                digest.update(chunk)
        report['files'].append({'database': name, 'path': str(target), 'size': target.stat().st_size, 'sha256': digest.hexdigest(), 'filestore_files': filestore_files, 'odoo_version': manifest.get('version')})
        print('Verified ' + name, file=sys.stderr, flush=True)
    except Exception as exc:
        report['errors'].append({'database': name, 'error': str(exc)})
(run / 'backup-report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
sys.exit(bool(report['errors']))
