"""Pinned tools: the JDK, Gradle and Android's command-line tools from tools.toml (downloaded, SHA-256-verified), and
the Android SDK packages tools.toml lists, installed by that sdkmanager at the pinned revisions.

Everything goes to $BSTACK_TOOLS_DIR if set, else <cache folder>/tools if one is configured (see paths.py), else
.tools/. That includes Gradle's own folder (downloaded libraries and plugins), the Android SDK, and emulators
(android-user/avd). Build output goes to .build/, a link into the cache folder. Nothing is installed globally, and
nothing large lands in the project or the home folder.

Usage: python3 scripts/tools.py <tool-name>     print the tool's folder, downloading it first if needed
       python3 scripts/tools.py sdk             install the Android SDK packages, and print the SDK's folder
       python3 scripts/tools.py gradle <args>   run Gradle on this project with the pinned tools (as check.py does)
"""
from pathlib import Path
import fcntl
import hashlib
import os
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


def tools_dir() -> Path:
    if os.environ.get('BSTACK_TOOLS_DIR'):
        return Path(os.environ['BSTACK_TOOLS_DIR'])
    cache = cache_root()
    return cache / 'tools' if cache else ROOT / '.tools'


def pins() -> dict:
    return tomllib.loads((ROOT / 'tools.toml').read_text())


def tool_path(name: str) -> Path:
    """The tool's folder (its `home` in tools.toml), downloaded and verified first if needed."""
    spec = pins()[name]
    folder = tools_dir() / f'{name}-{spec["version"]}'
    home = folder / spec['home']
    if (folder / '.complete').is_file():
        return home
    # Several runs (other checkouts too) share this folder: one downloads at a time, into a staging folder that is
    # renamed into place only once verified and unpacked, so no one sees a half-written tool.
    folder.parent.mkdir(parents=True, exist_ok=True)
    with (folder.parent / f'{name}.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (folder / '.complete').is_file():
            return home
        staging = Path(tempfile.mkdtemp(dir=folder.parent, prefix=f'.{name}-'))
        try:
            archive = staging / spec['url'].rsplit('/', 1)[-1]
            with urllib.request.urlopen(spec['url']) as response, archive.open('wb') as out:
                shutil.copyfileobj(response, out)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            if digest != spec['sha256']:
                sys.exit(f'{name}: checksum mismatch (expected {spec["sha256"]}, got {digest}). Refusing to use it.')
            unpacked = staging / 'tool'
            if archive.name.endswith('.zip'):
                # ditto keeps the permissions inside the archive (Gradle's and sdkmanager's launchers); zipfile doesn't.
                subprocess.run(['ditto', '-x', '-k', str(archive), str(unpacked)], check=True)
            else:
                with tarfile.open(archive) as tar:
                    tar.extractall(unpacked, filter='tar')
            (unpacked / '.complete').write_text(digest)
            if folder.exists():
                shutil.rmtree(folder)  # a partial folder from a run that crashed before this lock existed
            unpacked.rename(folder)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return home


def sdk_root() -> Path:
    return tools_dir() / 'android-sdk'


def installed_revision(package: str) -> str | None:
    properties = sdk_root() / package.replace(';', '/') / 'source.properties'
    if not properties.is_file():
        return None
    for line in properties.read_text().splitlines():
        if line.startswith('Pkg.Revision='):
            return line.split('=', 1)[1].strip()
    return None


def sdk() -> Path:
    """The Android SDK with tools.toml's packages at their pinned revisions, installed by the pinned sdkmanager."""
    wanted = pins()['android-sdk']['packages']
    root = sdk_root()
    root.mkdir(parents=True, exist_ok=True)
    with (root.parent / 'android-sdk.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        missing = [p for p, revision in wanted.items() if installed_revision(p) != revision]
        if missing:
            sdkmanager = tool_path('cmdline-tools') / 'bin/sdkmanager'
            env = tool_env()
            licenses = subprocess.run([str(sdkmanager), f'--sdk_root={root}', '--licenses'], input='y\n' * 50,
                                      env=env, capture_output=True, text=True)
            if licenses.returncode != 0:
                sys.exit(f'sdkmanager --licenses failed:\n{(licenses.stdout + licenses.stderr)[-2000:]}')
            proc = subprocess.run([str(sdkmanager), f'--sdk_root={root}', '--install', *missing], env=env,
                                  capture_output=True, text=True)
            if proc.returncode != 0:
                sys.exit(f'sdkmanager failed:\n{(proc.stdout + proc.stderr)[-3000:]}')
            moved = {p: installed_revision(p) for p in missing if installed_revision(p) != wanted[p]}
            if moved:
                sys.exit('Google has published newer Android SDK packages than tools.toml pins: ' +
                         ', '.join(f'{p} {got} (pinned {wanted[p]})' for p, got in moved.items()) +
                         '. Update the pins in tools.toml (a reviewed change), then run again.')
    return root


def tool_env() -> dict:
    """JAVA_HOME and the Android and Gradle folders, all in the tools folder, before the SDK is installed."""
    tools = tools_dir()
    jdk = tool_path('jdk')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('GRADLE_', 'ANDROID_', 'JAVA_', 'KOTLIN_'))}
    env.update({
        'JAVA_HOME': str(jdk),
        'ANDROID_HOME': str(sdk_root()),
        'ANDROID_SDK_ROOT': str(sdk_root()),
        'ANDROID_USER_HOME': str(tools / 'android-user'),
        'ANDROID_AVD_HOME': str(tools / 'android-user/avd'),
        'ANDROID_EMULATOR_HOME': str(tools / 'android-user'),
        'GRADLE_USER_HOME': str(tools / 'gradle-home'),
        'PATH': os.pathsep.join([str(jdk / 'bin'), str(sdk_root() / 'platform-tools'), env.get('PATH', '')]),
    })
    return env


def android_env() -> dict:
    """The environment for every Gradle, adb and emulator command: the pinned JDK, Gradle and SDK, everything in the
    tools folder, build output in .build/ (linked into the cache folder)."""
    link_build_dirs(ROOT)
    sdk()
    tool_path('gradle')
    return tool_env()


def gradle_command(*args: str) -> list[str]:
    """Gradle on this project. Its per-project cache and Kotlin's per-project files go in .build/ too."""
    return [str(tool_path('gradle') / 'bin/gradle'), '--project-dir', str(ROOT),
            '--project-cache-dir', str(ROOT / '.build/gradle-project'),
            f'-Pkotlin.project.persistent.dir={ROOT / ".build/kotlin"}', '--console=plain', *args]


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'gradle':
        env = android_env()
        sys.exit(subprocess.run(gradle_command(*sys.argv[2:]), env=env).returncode)
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(sdk() if sys.argv[1] == 'sdk' else tool_path(sys.argv[1]))
