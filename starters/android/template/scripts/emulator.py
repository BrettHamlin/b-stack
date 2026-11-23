"""The Android emulator that verify runs journeys on, and this Mac's lock on it.

One emulator (AVD `bstack-api37`, from tools.toml's system image) serves every checkout on the Mac. Its disk image and
settings live in the tools folder (android-user/avd), like the SDK. in_use() takes the machine-wide lock on it, so a
second run waits until the first finishes and says who holds it; the lock is an flock, released when its holder exits.
A running emulator is left running for the next run; `stop` shuts it down.

Using the emulator by hand (adb, screenshots, recordings) takes the same lock through `run`, the one supported route;
the lock can't stop tools run outside it. The command gets $ANDROID_SERIAL, so adb talks to that emulator.

Usage: python3 scripts/emulator.py run [--for SECONDS] -- COMMAND ...
       python3 scripts/emulator.py stop
"""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator
import argparse
import fcntl
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import android_env, pins, sdk_root, tool_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
AVD = 'bstack-api37'
HELD = 'BSTACK_EMULATOR_LOCK'  # set for children of the lock's holder, so they don't wait for it


def image() -> str:
    return next(p for p in pins()['android-sdk']['packages'] if p.startswith('system-images;'))


def adb(env: dict, *args: str, serial: str | None = None, timeout: float = 120) -> str:
    cmd = [str(sdk_root() / 'platform-tools/adb'), *(['-s', serial] if serial else []), *args]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    return proc.stdout + proc.stderr


def running(env: dict) -> str | None:
    """The serial of the running emulator for this AVD, if one is up."""
    for line in adb(env, 'devices').splitlines()[1:]:
        serial = line.split('\t')[0]
        if serial.startswith('emulator-') and line.endswith('device'):
            if adb(env, 'emu', 'avd', 'name', serial=serial).splitlines()[:1] == [AVD]:
                return serial
    return None


def create(env: dict) -> None:
    if (Path(env['ANDROID_AVD_HOME']) / f'{AVD}.ini').is_file():
        return
    avdmanager = tool_path('cmdline-tools') / 'bin/avdmanager'
    proc = subprocess.run([str(avdmanager), 'create', 'avd', '-n', AVD, '-k', image(), '-d', 'pixel_7'],
                          input='no\n', env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'avdmanager create failed:\n{(proc.stdout + proc.stderr)[-2000:]}')
    # avdmanager records the image relative to its own folder's parent (the tools folder), but the emulator reads it
    # relative to the SDK.
    config = Path(env['ANDROID_AVD_HOME']) / f'{AVD}.avd/config.ini'
    config.write_text(config.read_text().replace(f'image.sysdir.1={sdk_root().name}/', 'image.sysdir.1='))


def boot(env: dict) -> str:
    """The emulator's serial, booting it (headless) if it isn't running."""
    serial = running(env)
    if serial and adb(env, 'shell', 'getprop', 'sys.boot_completed', serial=serial).strip() == '1':
        return serial
    # One still starting (adb may not list it yet) is waited for, not started twice.
    starting = subprocess.run(['pgrep', '-f', '--', f'-avd {AVD}( |$)'], capture_output=True, text=True).stdout.split()
    if starting:
        return wait_for_boot(env, None)
    create(env)
    log = ROOT / '.build/emulator.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([str(sdk_root() / 'emulator/emulator'), '-avd', AVD, '-no-window', '-no-audio',
                             '-no-boot-anim', '-no-snapshot', '-gpu', 'swiftshader_indirect'],
                            env=env, stdout=log.open('w'), stderr=subprocess.STDOUT, start_new_session=True)
    return wait_for_boot(env, proc)


def wait_for_boot(env: dict, proc: subprocess.Popen | None) -> str:
    """The serial once the emulator has booted. One this run started is killed if it doesn't boot, or on Ctrl-C."""
    try:
        return booted(env, proc)
    except (SystemExit, KeyboardInterrupt):
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # it had already exited
        raise


def booted(env: dict, proc: subprocess.Popen | None) -> str:
    log = ROOT / '.build/emulator.log'
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            sys.exit(f'The emulator exited during boot (status {proc.returncode}); see {log}.')
        serial = running(env)
        if serial and adb(env, 'shell', 'getprop', 'sys.boot_completed', serial=serial).strip() == '1':
            return serial
        time.sleep(2)
    pids = subprocess.run(['pgrep', '-f', '--', f'-avd {AVD}( |$)'], capture_output=True, text=True).stdout.split()
    sys.exit(f'The emulator didn\'t boot in 5 minutes; see {log}. Its processes: {", ".join(pids) or "none"} '
             '(stop a stuck one with kill <pid>).')


def lock_file() -> Path:
    """Machine-wide, whatever cache folder each checkout configures: the emulator belongs to the user."""
    return Path.home() / 'Library/Caches/b-stack/emulators' / f'{AVD}.lock'


@contextmanager
def in_use(holder: str) -> Iterator[dict]:
    """Hold this machine's lock on the emulator, waiting while another process holds it. Yields the environment a child
    needs so it doesn't wait for the lock its parent holds (test_rules.py -> check.py -> verify.py)."""
    if os.environ.get(HELD):
        yield {HELD: '1'}
        return
    path = lock_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.seek(0)
            print(f'[emulator] waiting for the emulator: in use by {lock.read().strip() or "another process"}', flush=True)
            waited = time.monotonic()
            fcntl.flock(lock, fcntl.LOCK_EX)
            print(f'[emulator] got the emulator after {time.monotonic() - waited:.0f}s', flush=True)
        lock.truncate(0)
        lock.write(f'pid {os.getpid()}, {holder}, since {datetime.now().strftime("%H:%M:%S")}\n')
        lock.flush()
        try:
            yield {HELD: '1'}
        finally:
            lock.truncate(0)


def run(command: list[str], seconds: float | None) -> int:
    env = android_env()
    with in_use(f'emulator.py run in {ROOT}: {" ".join(command)[:100]}') as held:
        serial = boot(env)
        proc = subprocess.Popen(command, env={**env, **held, 'ANDROID_SERIAL': serial}, process_group=0)
        try:
            status = proc.wait(timeout=seconds)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as stopped:
            # The command's own group: stop it before the lock is released, so the next holder has the emulator alone.
            os.killpg(proc.pid, signal.SIGINT)
            try:
                status = proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                status = proc.wait()
            if isinstance(stopped, KeyboardInterrupt):
                raise
    return status if status >= 0 else 128 - status


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='action', required=True)
    use = commands.add_parser('run', help='run a command holding the emulator')
    use.add_argument('--for', dest='seconds', type=float, metavar='SECONDS')
    use.add_argument('command', nargs=argparse.REMAINDER)
    commands.add_parser('stop', help='shut the emulator down')
    args = parser.parse_args()
    if args.action == 'stop':
        environment = android_env()
        with in_use(f'emulator.py stop in {ROOT}'):
            if serial := running(environment):
                adb(environment, 'emu', 'kill', serial=serial)
        sys.exit(0)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('run needs a command, e.g. run -- adb shell screencap -p /sdcard/s.png')
    sys.exit(run(command, args.seconds))
