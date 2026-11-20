"""Where the research media (video, frames, slide captures) lives. It is never committed.

Configure it with $BSTACK_MEDIA_DIR, or `media_dir = "/path"` in ~/.config/b-stack/config.toml,
and the repo's artifacts/ becomes a link to it. With nothing configured, artifacts/ itself is the folder.
A configured folder that doesn't exist (e.g. an unmounted drive) is an error: never fall back elsewhere.
"""
from pathlib import Path
import os
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
ALIAS = ROOT / 'artifacts'
CONFIG = Path.home() / '.config/b-stack/config.toml'


def configured_media_dir() -> tuple[Path, str] | None:
    configured = os.environ.get('BSTACK_MEDIA_DIR')
    source = '$BSTACK_MEDIA_DIR'
    if not configured and CONFIG.is_file():
        configured = tomllib.loads(CONFIG.read_text()).get('media_dir')
        source = str(CONFIG)
    return (Path(configured).expanduser().resolve(), source) if configured else None


def media_root() -> Path:
    """The media folder, with artifacts/ pointing at it. Exits if a configured folder is unavailable."""
    configured = configured_media_dir()
    if configured is None:
        if ALIAS.is_symlink():
            sys.exit(f'{ALIAS} links to {os.readlink(ALIAS)}, but no media_dir is configured. '
                     f'Set media_dir in {CONFIG} (or $BSTACK_MEDIA_DIR), or remove the link to use artifacts/ as the folder.')
        return ALIAS
    root, source = configured
    if not root.is_dir():
        sys.exit(f'Media folder {root} (from {source}) is not available. Is its drive mounted?')
    if ALIAS.is_symlink():
        if ALIAS.resolve() == root.resolve():
            return root
        ALIAS.unlink()
    elif ALIAS.exists():
        sys.exit(f'{ALIAS} is a real folder but media_dir points to {root}. Move its contents there, then remove it.')
    ALIAS.symlink_to(root, target_is_directory=True)
    return root
