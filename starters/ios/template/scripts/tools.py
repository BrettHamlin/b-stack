"""Print the path to a pinned tool from tools.toml, downloading and SHA-256-verifying it first if needed.

Tools go to $BSTACK_TOOLS_DIR if set, else <cache folder>/tools if one is configured (see paths.py), else .tools/.

Usage: python3 scripts/tools.py <tool-name>
"""
from pathlib import Path
import fcntl
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import cache_root  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def tools_dir() -> Path:
    if os.environ.get('BSTACK_TOOLS_DIR'):
        return Path(os.environ['BSTACK_TOOLS_DIR'])
    cache = cache_root()
    return cache / 'tools' if cache else ROOT / '.tools'


def tool_path(name: str) -> Path:
    spec = tomllib.loads((ROOT / 'tools.toml').read_text())[name]
    home = tools_dir() / f'{name}-{spec["version"]}'
    binary = home / spec['binary']
    if binary.is_file():
        return binary
    # Several runs (other checkouts too) share this folder: one downloads at a time, into a staging folder that is
    # renamed into place only once verified and unpacked, so no one sees a half-written tool.
    home.parent.mkdir(parents=True, exist_ok=True)
    with (home.parent / f'{name}.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if binary.is_file():
            return binary
        staging = Path(tempfile.mkdtemp(dir=home.parent, prefix=f'.{name}-'))
        try:
            archive = staging / 'download.zip'
            with urllib.request.urlopen(spec['url']) as response, archive.open('wb') as out:
                shutil.copyfileobj(response, out)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            if digest != spec['sha256']:
                sys.exit(f'{name}: checksum mismatch (expected {spec["sha256"]}, got {digest}). Refusing to use it.')
            unpacked = staging / 'tool'
            # ditto keeps the symlinks and permissions inside macOS frameworks; zipfile does not.
            subprocess.run(['ditto', '-x', '-k', str(archive), str(unpacked)], check=True)
            (unpacked / spec['binary']).chmod(0o755)
            if home.exists():
                shutil.rmtree(home)  # a partial folder from a run that crashed before this lock existed
            unpacked.rename(home)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return binary


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(tool_path(sys.argv[1]))
