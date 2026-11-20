"""Observe mode: record whether the gates ran on the code an agent hands back or commits. Never blocks.

check.py records every run: the gates, the failures, and a fingerprint of the project's files. At each hand-back
(the Claude Code Stop hook in .claude/settings.json) this compares the files with the last run and appends one line
to .build/handbacks.jsonl:
  checked     every gate ran and passed on exactly these files
  partial     the last run was on these files but skipped a gate or failed one
  unchecked   the files changed after the last run (or check.py never ran)
  unchanged   nothing changed since the previous hand-back (left out of the summary)
The commit-msg git hook (.githooks/commit-msg) adds the same verdict to the commit as a `Checked:` trailer,
so unchecked commits can be found with `git log --grep "Checked: unchecked"`.

Usage:
  python3 scripts/handback.py stop            the Stop hook (reads the hook's JSON on stdin)
  python3 scripts/handback.py stamp <file>    the commit-msg hook
  python3 scripts/handback.py summary         counts so far
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GATES = ['compiler', 'tuist', 'swiftlint', 'harmonize', 'tests', 'verify']


def state_dir(root: Path) -> Path:
    path = root / '.build'
    path.mkdir(parents=True, exist_ok=True)
    return path


def fingerprint(root: Path) -> str | None:
    """Hash of every tracked and untracked, non-ignored file's path and content. None outside a git repo."""
    proc = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                          cwd=root, capture_output=True)
    if proc.returncode != 0:
        return None
    digest = hashlib.sha256()
    for name in sorted(set(proc.stdout.decode().split('\0')) - {''}):
        path = root / name
        if path.is_file() and not path.is_symlink():
            digest.update(name.encode() + b'\0' + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def record_check(root: Path, gates: list[str], failed: list[str]) -> None:
    """Called by check.py after every run."""
    run = {'fingerprint': fingerprint(root), 'gates': gates, 'failed': failed, 'time': now()}
    (state_dir(root) / 'last-check.json').write_text(json.dumps(run))


def verdict(root: Path) -> tuple[str, str | None]:
    current = fingerprint(root)
    last = read(state_dir(root) / 'last-check.json')
    if current is None or last.get('fingerprint') != current:
        return 'unchecked', current
    if set(GATES) <= set(last.get('gates', [])) and not last.get('failed'):
        return 'checked', current
    return 'partial', current


def stop(root: Path, hook_input: dict) -> dict:
    status, current = verdict(root)
    previous = read(state_dir(root) / 'last-handback.json')
    clean = subprocess.run(['git', 'status', '--porcelain'], cwd=root, capture_output=True, text=True).stdout == ''
    if current is not None and (previous.get('fingerprint') == current or (not previous and clean)):
        status = 'unchanged'
    last = read(state_dir(root) / 'last-check.json')
    entry = {'time': now(), 'status': status, 'session': hook_input.get('session_id'),
             'last_check_gates': last.get('gates'), 'last_check_failed': last.get('failed')}
    with (state_dir(root) / 'handbacks.jsonl').open('a') as log:
        log.write(json.dumps(entry) + '\n')
    (state_dir(root) / 'last-handback.json').write_text(json.dumps({'fingerprint': current}))
    return entry


def stamp(root: Path, message_file: Path) -> None:
    message = message_file.read_text()
    if '\nChecked: ' in message:
        return
    status, _ = verdict(root)
    trailer = f'Checked: {status}'
    if status == 'partial':
        last = read(state_dir(root) / 'last-check.json')
        trailer += f' (gates {",".join(last.get("gates", []))}; failed {",".join(last.get("failed", [])) or "none"})'
    subprocess.run(['git', 'interpret-trailers', '--in-place', '--trailer', trailer, str(message_file)], cwd=root, check=True)


def summary(root: Path) -> str:
    path = state_dir(root) / 'handbacks.jsonl'
    entries = [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []
    counted = [e for e in entries if e['status'] != 'unchanged']
    counts = {s: sum(e['status'] == s for e in counted) for s in ('checked', 'partial', 'unchecked')}
    rate = f'{100 * counts["unchecked"] / len(counted):.0f}%' if counted else 'n/a'
    return f'hand-backs: {len(counted)}  checked: {counts["checked"]}  partial: {counts["partial"]}  ' \
           f'unchecked: {counts["unchecked"]}  unchecked rate: {rate}'


def read(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    try:
        if command == 'stop':
            try:
                hook_input = json.loads(sys.stdin.read() or '{}')
            except ValueError:
                hook_input = {}
            stop(ROOT, hook_input)
        elif command == 'stamp':
            stamp(ROOT, Path(sys.argv[2]))
        elif command == 'summary':
            print(summary(ROOT))
        else:
            sys.exit(__doc__)
    except Exception as error:  # observe mode: a broken log must never block a hand-back or a commit
        print(f'handback.py {command}: {error}', file=sys.stderr)
    sys.exit(0)
