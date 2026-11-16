"""Where large, regenerable files go: build output, package checkouts, downloaded tools.

If a cache folder is configured, they go there and the project's .build/ (and Tuist/.build/) become links into it.
Configure it with $BSTACK_CACHE_DIR, or `cache_dir = "/path"` in ~/.config/b-stack/config.toml.
With nothing configured, everything stays inside the project (the default for a fresh clone).
A configured folder that doesn't exist (e.g. an unmounted drive) is an error: never fall back to the internal drive.
"""
from pathlib import Path
import hashlib
import os
import shutil
import sys
import tomllib

CONFIG = Path.home() / '.config/b-stack/config.toml'


def cache_root() -> Path | None:
    configured = os.environ.get('BSTACK_CACHE_DIR')
    source = '$BSTACK_CACHE_DIR'
    if not configured and CONFIG.is_file():
        configured = tomllib.loads(CONFIG.read_text()).get('cache_dir')
        source = str(CONFIG)
    if not configured:
        return None
    root = Path(configured).expanduser()
    if not root.is_dir():
        sys.exit(f'Cache folder {root} (from {source}) is not available. Is its drive mounted? '
                 'Refusing to put build output anywhere else.')
    return root


def project_cache(project: Path) -> Path | None:
    root = cache_root()
    if root is None:
        return None
    project = project.resolve()
    key = f'{project.name}-{hashlib.sha256(str(project).encode()).hexdigest()[:8]}'
    return root / 'projects' / key


def link_build_dirs(project: Path) -> None:
    """Point the project's build folders into the cache folder, if one is configured."""
    cache = project_cache(project)
    if cache is None:
        return
    links = {'.build': 'build'}
    if (project / 'Tuist/Package.swift').is_file():
        links['Tuist/.build'] = 'tuist-build'
    for link, target in links.items():
        path, destination = project / link, cache / target
        destination.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            if path.resolve() == destination.resolve():
                continue
            path.unlink()
        elif path.exists():
            shutil.rmtree(path)  # regenerable build output; the cache folder replaces it
        path.symlink_to(destination, target_is_directory=True)
