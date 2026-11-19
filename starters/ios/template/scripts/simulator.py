"""Pick the iOS Simulator that gates and verification run on."""
import json
import os
import re
import subprocess
import sys


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
