"""Pick the iOS Simulator that gates and verification run on, and hold it while using it.

A simulator is shared by every checkout on the Mac: two test runs on one simulator kill each other's test runner
("Test crashed with signal kill before establishing connection"). in_use() takes this machine's lock on it, so a second
run waits until the first finishes and says who holds it. The lock is an flock, so it is released when its holder exits
or is killed. Its descriptor isn't inherited (a simulator helper could keep it forever), so killing only the holder,
not its process group as Ctrl-C does, frees the simulator while a child may still be using it.

Using the simulator by hand (agent-device, xcrun simctl, screen recordings) takes the same lock through `run`, the one
supported route; the lock can't stop tools run outside it. The command gets $BSTACK_SIMULATOR_ID, so it can name the
simulator, and the scripts it starts (verify.py launch) don't wait for the lock it holds.

Usage: python3 scripts/simulator.py run [--for SECONDS] -- COMMAND ...
  --for SECONDS  interrupt the command (Ctrl-C) after SECONDS, e.g. to end a screen recording
"""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator
import argparse
import fcntl
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
HELD = 'BSTACK_SIMULATOR_LOCKS'  # simulators an ancestor process holds, comma-separated; its children don't wait for them


def simulator() -> str:
    """$BSTACK_SIMULATOR_ID if set, else the first available iPhone simulator on the newest standard iOS runtime.

    Device-specific runtimes (e.g. "...iOS-27-2-iPhone19-4") are skipped: their devices can fail to prepare for tests.
    """
    if os.environ.get('BSTACK_SIMULATOR_ID'):
        return os.environ['BSTACK_SIMULATOR_ID']
    for udid, _ in devices():
        return udid
    sys.exit('No available iPhone simulator. Install an iOS runtime in Xcode.')


def devices() -> list[tuple[str, dict]]:
    """Available iPhone simulators on standard iOS runtimes, newest runtime first, as (udid, device info)."""
    listing = json.loads(subprocess.run(['xcrun', 'simctl', 'list', 'devices', 'available', '-j'],
                                        capture_output=True, text=True, check=True).stdout)['devices']
    standard = {r: tuple(map(int, m.groups())) for r in listing if (m := re.search(r'SimRuntime\.iOS-(\d+)-(\d+)$', r))}
    found = []
    for runtime in sorted(standard, key=standard.get, reverse=True):
        for device in listing[runtime]:
            if re.match(r'iPhone \d', device['name']) and 'b-stack verify' not in device['name']:  # not verify's clones
                found.append((device['udid'], {**device, 'runtime': runtime.rsplit('.', 1)[-1]}))
    return found


def state(udid: str) -> dict:
    """The device's simctl entry (name, state, ...), or {} if it isn't available."""
    listing = json.loads(subprocess.run(['xcrun', 'simctl', 'list', 'devices', '-j'],
                                        capture_output=True, text=True, check=True).stdout)['devices']
    for runtime, entries in listing.items():
        for device in entries:
            if device['udid'] == udid:
                return {**device, 'runtime': runtime.rsplit('.', 1)[-1]}
    return {}


def lock_file(udid: str) -> Path:
    """Machine-wide, whatever cache folder each checkout configures: simulators belong to the user, not a checkout."""
    return Path.home() / 'Library/Caches/b-stack/simulators' / f'{udid}.lock'


@contextmanager
def in_use(udid: str, holder: str, stop: threading.Event | None = None) -> Iterator[dict]:
    """Hold this machine's lock on simulator `udid`, waiting while another process holds it. `holder` says who is
    using it (e.g. "check.py in /path/to/checkout"), for anyone who has to wait. A thread waiting for it stops with
    KeyboardInterrupt once `stop` is set (Ctrl-C reaches only the main thread).

    Yields the environment a child process needs so it doesn't wait for the lock its parent holds (check.py -> verify.py,
    test_rules.py -> check.py). A process whose ancestor holds the lock yields at once.
    """
    held = [u for u in os.environ.get(HELD, '').split(',') if u]
    env = {HELD: ','.join(dict.fromkeys(held + [udid]))}
    if udid in held:
        yield env
        return
    path = lock_file(udid)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as lock:
        if not try_lock(lock):
            stop = stop or threading.Event()
            waited = time.monotonic()
            for _ in range(2):  # a holder that took the lock a moment ago may not have written its name yet
                lock.seek(0)
                if (current := lock.read().strip()) or stop.wait(1):
                    break
            print(f'[simulator] waiting for simulator {udid}: in use by {current or "another process"}', flush=True)
            while not try_lock(lock):
                if stop.wait(1):
                    raise KeyboardInterrupt
            print(f'[simulator] got simulator {udid} after {time.monotonic() - waited:.0f}s', flush=True)
        lock.truncate(0)
        lock.write(f'pid {os.getpid()}, {holder}, since {datetime.now().strftime("%H:%M:%S")}\n')
        lock.flush()
        try:
            yield env
        finally:
            lock.truncate(0)


def try_lock(lock) -> bool:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def run(command: list[str], seconds: float | None = None) -> int:
    """Run `command` holding this Mac's lock on the simulator, and return its exit status. Waits while another process
    holds the lock. The command runs in its own process group, so Ctrl-C or `kill` of this process, and the end of
    `seconds`, reach every process it started (a recording started by a shell, too)."""
    udid = simulator()
    described = shlex.join(command)
    with in_use(udid, f'simulator.py run in {ROOT}: {described[:100]}') as held:
        print(f'[simulator] holding simulator {udid} for: {described}', flush=True)
        proc = subprocess.Popen(command, env={**os.environ, **held, 'BSTACK_SIMULATOR_ID': udid}, process_group=0)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda signum, _: interrupt(proc, signum))
        try:
            status = proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            interrupt(proc, signal.SIGINT)
            status = proc.wait()
    print(f'[simulator] released simulator {udid}', flush=True)
    return status if status >= 0 else 128 - status


def interrupt(proc: subprocess.Popen, signum: int) -> None:
    try:
        os.killpg(proc.pid, signum)
    except ProcessLookupError:  # already gone
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='action', required=True)
    use = commands.add_parser('run', help='run a command holding the simulator')
    use.add_argument('--for', dest='seconds', type=float, metavar='SECONDS',
                     help='interrupt the command (Ctrl-C) after SECONDS')
    use.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('run needs a command, e.g. run -- agent-device snapshot --platform ios --udid <udid>')
    try:
        sys.exit(run(command, args.seconds))
    except KeyboardInterrupt:
        sys.exit('\nStopped.')
