#!/usr/bin/env python3
"""Create server backups, then fetch verified ZIPs for Google Drive upload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import paramiko

parser = argparse.ArgumentParser()
parser.add_argument('--install', action='store_true')
parser.add_argument('--output', required=True)
parser.add_argument('--resume', help='Existing server run timestamp to download without creating new backups')
args = parser.parse_args()
os.umask(0o077)
here = Path(__file__).resolve().parent
notes = (here.parents[3] / '_docs/ssh/ssh.md').read_text()
match = re.search(r'ssh root@72\.61\.186\.1\s*\n\s*\n([^\n`]+)', notes)
if not match:
    raise RuntimeError('Cannot locate SSH credential in connection notes')
client = paramiko.SSHClient()
client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect('72.61.186.1', username='root', password=match.group(1).strip(), look_for_keys=False, allow_agent=False, timeout=20)
try:
    sftp = client.open_sftp()
    remote = '/usr/local/sbin/odoo-backup-all.py'
    if args.install:
        sftp.put(str(here / 'backup_all.py'), remote)
        sftp.chmod(remote, 0o700)
    if args.resume:
        if not re.fullmatch(r'[0-9]{8}T[0-9]{6}\.[0-9]{6}Z', args.resume):
            raise ValueError('Invalid run timestamp')
        with sftp.open('/var/backups/odoo/' + args.resume + '/backup-report.json') as saved:
            report = json.load(saved)
        status = int(bool(report['errors']))
    else:
        stdin, stdout, stderr = client.exec_command('python3 /usr/local/sbin/odoo-backup-all.py')
        # Drain both streams without risking pipe-buffer deadlocks.
        import time
        channel = stdout.channel
        result = bytearray()
        while not channel.exit_status_ready() or channel.recv_ready() or channel.recv_stderr_ready():
            if channel.recv_ready():
                result.extend(channel.recv(65536))
            if channel.recv_stderr_ready():
                sys.stderr.write(channel.recv_stderr(65536).decode(errors='replace'))
                sys.stderr.flush()
            time.sleep(0.1)
        status = channel.recv_exit_status()
        report = json.loads(result)
    dest = Path(args.output).resolve() / Path(report['run']).name
    dest.mkdir(parents=True, exist_ok=True)
    for item in report['files']:
        local = dest / Path(item['path']).name
        partial = local.with_suffix('.zip.partial')
        sftp.get(item['path'], str(partial))
        digest = hashlib.sha256()
        with partial.open('rb') as content:
            for chunk in iter(lambda: content.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != item['sha256']:
            raise RuntimeError('Download checksum mismatch: ' + item['database'])
        partial.rename(local)
        item['local_path'] = str(local)
        print('Downloaded and verified ' + item['database'], file=sys.stderr, flush=True)
    (dest / 'backup-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    sys.exit(status)
finally:
    client.close()
