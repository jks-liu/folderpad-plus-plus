"""Validate the prepared entry using the official nppPluginList validator.

Usage (dependencies: the official requirements.txt in an isolated venv):
  python tools/validate-plugin-list.py --official-dir .cache/release-tools
The directory must contain validator.py, pl.schema and pl.x64.json downloaded
from notepad-plus-plus/nppPluginList. All validator writes stay in a new build
directory. The exact release ZIP is served on loopback; public URL verification
is a separate post-upload step: tools/prepare-release.ps1 -VerifyPublished.
"""
import argparse
import functools
import hashlib
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-dir', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    official = Path(args.official_dir).resolve()
    entry = json.loads((root / 'dist/nppPluginList-entry-x64.json').read_text(encoding='utf-8'))
    current = json.loads((official / 'pl.x64.json').read_text(encoding='utf-8-sig'))
    for field in ('folder-name', 'display-name', 'repository'):
        assert all(plugin[field] != entry[field] for plugin in current['npp-plugins']), f'Duplicate {field}'
    archive = root / 'dist' / f'folderpad++-{entry["version"]}-x64.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == entry['id'], 'ZIP hash mismatch'
    base = root / 'build' / ('plugin-list-validation-' + time.strftime('%Y%m%d-%H%M%S'))
    (base / 'src').mkdir(parents=True)
    (base / 'doc').mkdir()
    for filename in ('validator.py', 'pl.schema'):
        shutil.copy2(official / filename, base / filename)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    handler = functools.partial(Handler, directory=str(root / 'dist'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    local_entry = dict(entry, repository=f'http://127.0.0.1:{server.server_port}/{archive.name}')
    candidate = dict(current, **{'npp-plugins': [local_entry]})
    (base / 'src/pl.x64.json').write_text(json.dumps(candidate, indent=2), encoding='utf-8')
    try:
        result = subprocess.run([sys.executable, 'validator.py', 'x64'], cwd=base,
                                capture_output=True, text=True, encoding='utf-8', timeout=120)
    finally:
        server.shutdown()
        server.server_close()
    (base / 'validator.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    report = {'status': 'passed' if result.returncode == 0 else 'failed',
              'entryVersion': entry['version'], 'zipSHA256': entry['id'],
              'checks': ['uniqueness against current official x64 list',
                         'official schema, ZIP download/hash, root DLL name and FileVersion'],
              'publicDownloadVerified': False, 'artifacts': str(base),
              'officialValidatorSHA256': hashlib.sha256((official / 'validator.py').read_bytes()).hexdigest(),
              'officialSchemaSHA256': hashlib.sha256((official / 'pl.schema').read_bytes()).hexdigest(),
              'officialListSHA256': hashlib.sha256((official / 'pl.x64.json').read_bytes()).hexdigest()}
    (base / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(result.stdout + result.stderr)
    print(json.dumps(report, indent=2))
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
