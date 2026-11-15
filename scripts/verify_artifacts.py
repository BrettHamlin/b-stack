"""Verify external artifact availability; --hash also verifies full content."""
from pathlib import Path
import argparse
import hashlib
import json
import os

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--hash', action='store_true', help='Verify SHA-256 for all artifacts')
args = parser.parse_args()
project = Path(__file__).resolve().parents[1]
manifest = json.loads((project / 'ARTIFACTS.json').read_text())
root = Path(os.environ.get('B_STACK_MEDIA_ROOT') or os.environ.get('POTATO_MEDIA_ROOT') or manifest['media_root'])
if not root.is_dir():
    raise SystemExit(f'Media directory unavailable: {root}. Mount MicroBay or set B_STACK_MEDIA_ROOT.')
errors = []
for entry in manifest['files']:
    path = root / entry['path']
    if not path.is_file():
        errors.append(f'Missing: {path}')
    elif path.stat().st_size != entry['bytes']:
        errors.append(f'Size changed: {path}')
    elif args.hash:
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != entry['sha256']:
                errors.append(f'Hash mismatch: {path}')
if errors:
    raise SystemExit('\n'.join(errors))
total = sum(entry['bytes'] for entry in manifest['files'])
print(f"Verified {len(manifest['files'])} external artifacts ({total / 1024**2:.1f} MiB)" + (' with SHA-256.' if args.hash else '.'))
