"""Pinned tools: the Rust toolchain from rust-toolchain.toml, and the tools in tools.toml (downloaded, SHA-256-verified).

Everything goes to $BSTACK_TOOLS_DIR if set, else <cache folder>/tools if one is configured (see paths.py), else
.tools/. That includes the toolchain (RUSTUP_HOME) and Cargo's downloaded crates (CARGO_HOME): nothing goes to
~/.rustup or ~/.cargo. Needs rustup on the machine (https://rustup.rs) to install the pinned toolchain; rustup checks
each component against the release's published hashes.

Usage: python3 scripts/tools.py <tool-name>     print the tool's path, downloading it first if needed
       python3 scripts/tools.py rust            install the pinned toolchain if needed and print its bin folder
"""
from pathlib import Path
import fcntl
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import cache_root, link_build_dirs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {('Darwin', 'arm64'): 'mac-arm64', ('Linux', 'x86_64'): 'linux-x64'}
# Inherited settings that change what cargo, rustc, rustdoc or clippy check, or what runs the tests. rust_env() drops
# them: the gates run with the project's settings only (scripts/settings.py records those).
INHERITED = re.compile(r'^(CARGO_(BUILD|PROFILE|TARGET|ENCODED|UNSTABLE|ALIAS)_.*|RUSTC|RUSTDOC|RUSTC_WRAPPER|'
                       r'RUSTC_WORKSPACE_WRAPPER|RUSTC_BOOTSTRAP|RUSTFLAGS|RUSTDOCFLAGS|CLIPPY_.*|RUST_TEST_.*)$')


def tools_dir() -> Path:
    if os.environ.get('BSTACK_TOOLS_DIR'):
        return Path(os.environ['BSTACK_TOOLS_DIR'])
    cache = cache_root()
    return cache / 'tools' if cache else ROOT / '.tools'


def unpack(archive: Path, into: Path) -> None:
    if archive.name.endswith('.zip'):
        # ditto keeps the symlinks and permissions inside macOS bundles; zipfile does not.
        subprocess.run(['ditto', '-x', '-k', str(archive), str(into)], check=True)
    else:
        with tarfile.open(archive) as tar:
            tar.extractall(into, filter='data')


def host() -> str:
    """This machine's name in tools.toml (mac-arm64 or linux-x64)."""
    found = HOSTS.get((platform.system(), platform.machine()))
    if not found:
        sys.exit(f'No tools are pinned for {platform.system()} {platform.machine()}: tools.toml has '
                 f'{", ".join(HOSTS.values())}.')
    return found


def spec_for(name: str) -> dict:
    """The tool's pin, with this machine's own table (url, sha256, binary) if it is built per machine."""
    spec = tomllib.loads((ROOT / 'tools.toml').read_text())[name]
    hosts = [h for h in HOSTS.values() if h in spec]
    if not hosts:
        return spec
    if host() not in spec:
        sys.exit(f'tools.toml pins {name} for {", ".join(hosts)}, not {host()}.')
    return {**{k: v for k, v in spec.items() if k not in hosts}, **spec[host()]}


def tool_path(name: str) -> Path:
    spec = spec_for(name)
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
            archive = staging / spec['url'].rsplit('/', 1)[-1]
            with urllib.request.urlopen(spec['url']) as response, archive.open('wb') as out:
                shutil.copyfileobj(response, out)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            if digest != spec['sha256']:
                sys.exit(f'{name}: checksum mismatch (expected {spec["sha256"]}, got {digest}). Refusing to use it.')
            unpacked = staging / 'tool'
            unpack(archive, unpacked)
            (unpacked / spec['binary']).chmod(0o755)
            if home.exists():
                shutil.rmtree(home)  # a partial folder from a run that crashed before this lock existed
            unpacked.rename(home)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return binary


def rustup() -> str:
    found = shutil.which('rustup') or str(Path.home() / '.cargo/bin/rustup')
    if not Path(found).is_file():
        sys.exit('rustup is not installed. Install it from https://rustup.rs; it installs the pinned toolchain here.')
    return found


def rust_env() -> dict:
    """The environment for every cargo command: the pinned toolchain first on PATH, its homes in the tools folder, and
    the project's build folder linked into the cache folder."""
    link_build_dirs(ROOT)
    channel = tomllib.loads((ROOT / 'rust-toolchain.toml').read_text())['toolchain']['channel']
    homes = tools_dir() / 'rust'
    env = {**{k: v for k, v in os.environ.items() if not INHERITED.match(k)}, 'RUSTUP_HOME': str(homes / 'rustup'),
           'CARGO_HOME': str(homes / 'cargo'), 'RUSTUP_TOOLCHAIN': channel}
    homes.mkdir(parents=True, exist_ok=True)
    with (homes / 'install.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # one install at a time across checkouts
        bin_dir = Path(env['RUSTUP_HOME']) / 'toolchains'
        installed = [p for p in bin_dir.glob(f'{channel}-*') if (p / 'bin/cargo-clippy').is_file()] if bin_dir.is_dir() else []
        if not installed:
            subprocess.run([rustup(), 'toolchain', 'install', channel, '--profile', 'minimal', '--component', 'clippy',
                            '--no-self-update'], env=env, check=True, stdout=sys.stderr)
            installed = [p for p in bin_dir.glob(f'{channel}-*') if (p / 'bin/cargo-clippy').is_file()]
    toolchain = installed[0]
    env['PATH'] = f'{toolchain / "bin"}{os.pathsep}{env.get("PATH", "")}'
    # Build output in .build/ (a link into the cache folder, see paths.py), and every warning is an error.
    env['CARGO_TARGET_DIR'] = str(ROOT / '.build/target')
    env['RUSTFLAGS'] = env['RUSTDOCFLAGS'] = '-D warnings'
    # clippy.toml is the root one for every crate: without this, Clippy 1.99.0 reads the nearest clippy.toml above
    # each crate's manifest, so a crate could bring one that drops the bans.
    env['CLIPPY_CONF_DIR'] = str(ROOT)
    if Path('/usr/bin/cc').is_file():
        # The system linker by path: a `cc` earlier on PATH (a shell helper, say) must not stand in for it.
        host = toolchain.name.removeprefix(f'{channel}-')
        env[f'CARGO_TARGET_{host.upper().replace("-", "_")}_LINKER'] = '/usr/bin/cc'
        env.setdefault('CC', '/usr/bin/cc')
    return env


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if sys.argv[1] == 'rust':
        print(rust_env()['PATH'].split(os.pathsep)[0])
    else:
        print(tool_path(sys.argv[1]))
