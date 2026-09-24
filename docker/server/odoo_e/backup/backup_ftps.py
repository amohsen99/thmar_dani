#!/usr/bin/env python3
"""Server-side Odoo backup and encrypted FTP delivery; no desktop dependency."""
import argparse
import datetime
import fcntl
import ftplib
import hashlib
import json
import os
from pathlib import Path
import ssl
import subprocess

ROOT = Path('/var/backups/odoo')
CONFIG = Path('/etc/odoo-backup-ftps.json')


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as content:
        for chunk in iter(lambda: content.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def enter_directory(ftp, name):
    try:
        ftp.cwd(name)
    except ftplib.error_perm:
        ftp.mkd(name)
        ftp.cwd(name)


def upload_run(settings, run):
    report = json.loads((run / 'backup-report.json').read_text())
    if report['errors'] or len(report['files']) != len(report['databases']):
        raise RuntimeError('Incomplete backup: ' + run.name)
    context = ssl.create_default_context()
    if not settings.get('verify_certificate', True):
        # Explicitly authorized by the user for this FTPS destination.
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    with ftplib.FTP_TLS(context=context, timeout=120) as ftp:
        ftp.connect(settings['host'], settings.get('port', 21))
        ftp.login(settings['username'], settings['password'])
        ftp.prot_p()  # Encrypt data transfers too; never fall back to plain FTP.
        ftp.set_pasv(True)
        if settings['directory'].startswith('/'):
            ftp.cwd('/')
        for part in settings['directory'].strip('/').split('/'):
            if part in ('', '.', '..') or '\r' in part or '\n' in part:
                raise ValueError('Unsafe destination directory')
            enter_directory(ftp, part)
        enter_directory(ftp, run.name)
        receipt_path = run / 'ftps-receipt.json'
        receipt = {'destination': settings['host'], 'directory': ftp.pwd(), 'files': []}
        expected = [(Path(item['path']), item['sha256']) for item in report['files']]
        expected.append((run / 'backup-report.json', sha256(run / 'backup-report.json')))
        for source, checksum in expected:
            if source.parent != run or any(c in source.name for c in '\r\n'):
                raise ValueError('Unsafe backup path')
            if sha256(source) != checksum:
                raise RuntimeError('Local checksum mismatch: ' + source.name)
            ftp.voidcmd('TYPE I')
            # Verify any existing completed file to resume safely without duplicates.
            existing_ok = False
            try:
                if ftp.size(source.name) == source.stat().st_size:
                    digest = hashlib.sha256()
                    ftp.retrbinary('RETR ' + source.name, digest.update, blocksize=262144)
                    existing_ok = digest.hexdigest() == checksum
                    if not existing_ok:
                        raise RuntimeError('Existing remote file differs: ' + source.name)
            except ftplib.error_perm as exc:
                if not str(exc).startswith('550'):
                    raise
            if not existing_ok:
                temporary = source.name + '.partial'
                with source.open('rb') as content:
                    ftp.storbinary('STOR ' + temporary, content, blocksize=262144)
                ftp.voidcmd('TYPE I')
                if ftp.size(temporary) != source.stat().st_size:
                    raise RuntimeError('Remote size mismatch: ' + source.name)
                digest = hashlib.sha256()
                ftp.retrbinary('RETR ' + temporary, digest.update, blocksize=262144)
                if digest.hexdigest() != checksum:
                    raise RuntimeError('Remote checksum mismatch: ' + source.name)
                ftp.rename(temporary, source.name)
            receipt['files'].append({'name': source.name, 'size': source.stat().st_size, 'sha256': checksum})
            save_json(receipt_path, receipt)
            print('Uploaded and SHA-256 verified: ' + source.name, flush=True)
        receipt['completed_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_json(receipt_path, receipt)
        (run / '.ftps-pending').unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', help='Existing backup run directory name; do not create another backup')
    args = parser.parse_args()
    os.umask(0o077)
    ROOT.mkdir(parents=True, exist_ok=True)
    settings = json.loads(CONFIG.read_text())
    with (ROOT / '.ftps.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.resume:
            if Path(args.resume).name != args.resume or args.resume in ('.', '..'):
                raise ValueError('Invalid run name')
            run = ROOT / args.resume
        else:
            result = subprocess.run(['python3', '/usr/local/sbin/odoo-backup-all.py'], stdout=subprocess.PIPE, text=True, check=True)
            run = Path(json.loads(result.stdout)['run'])
        (run / '.ftps-pending').touch()
        failures = []
        for marker in sorted(ROOT.glob('*/.ftps-pending')):
            try:
                upload_run(settings, marker.parent)
            except Exception as exc:
                print('Upload failed for ' + marker.parent.name + ': ' + str(exc), flush=True)
                failures.append(marker.parent.name)
        if failures:
            raise RuntimeError('Pending uploads retained locally: ' + ', '.join(failures))


if __name__ == '__main__':
    main()
