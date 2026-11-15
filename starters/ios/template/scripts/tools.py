"""Print the path to a pinned tool from tools.toml, downloading and SHA-256-verifying it into .tools/ (or $BSTACK_TOOLS_DIR) first if needed.

Usage: python3 scripts/tools.py <tool-name>
"""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def tool_path(name: str) -> Path:
    spec = tomllib.loads((ROOT / 'tools.toml').read_text())[name]
    home = Path(os.environ.get('BSTACK_TOOLS_DIR', ROOT / '.tools')) / f'{name}-{spec["version"]}'
    binary = home / spec['binary']
    if binary.is_file():
        return binary
    home.mkdir(parents=True, exist_ok=True)
    archive = home / 'download.zip'
    with urllib.request.urlopen(spec['url']) as response, archive.open('wb') as out:
        shutil.copyfileobj(response, out)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != spec['sha256']:
        shutil.rmtree(home)
        sys.exit(f'{name}: checksum mismatch (expected {spec["sha256"]}, got {digest}). Refusing to use it.')
    # ditto keeps the symlinks and permissions inside macOS frameworks; zipfile does not.
    subprocess.run(['ditto', '-x', '-k', str(archive), str(home)], check=True)
    archive.unlink()
    binary.chmod(0o755)
    return binary


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(tool_path(sys.argv[1]))
