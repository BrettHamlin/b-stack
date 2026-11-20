"""Verify external artifact availability; --hash also verifies full content."""
from pathlib import Path
import argparse
import hashlib
import json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--hash', action='store_true', help='Verify SHA-256 for all artifacts')
args = parser.parse_args()
from media import CONFIG, ROOT, media_root

manifest = json.loads((ROOT / 'ARTIFACTS.json').read_text())
root = media_root()
if not root.is_dir():
    raise SystemExit(f'No media at {root}. Put it there, or set media_dir in {CONFIG} (or $BSTACK_MEDIA_DIR).')
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
