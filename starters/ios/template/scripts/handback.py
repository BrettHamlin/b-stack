"""Observe mode: record whether the gates ran on the code an agent hands back or commits. Never blocks.

The verdict follows the code, not the moment: check.py records every run against the git tree of the project's files
(tracked and untracked, not ignored: the tree a commit of everything would have). Any commit, on any branch, from a
squash merge or made before the check, is checked if a passing run had exactly its tree:
  checked     every gate ran and passed on exactly these files
  partial     a run had these files but skipped a gate or failed one
  unchecked   no run had these files (they changed after the last run, or check.py never ran)
At each Claude Code hand-back (the Stop hook in .claude/settings.json) one line per checkout the session worked in goes
to handbacks.jsonl; `unchanged` means that checkout's files are as they were at its previous hand-back (left out of the
summary). The commit-msg git hook (.githooks/commit-msg) adds the committed tree's verdict as a `Checked:` trailer.

The records live in the clone's git folder (`git rev-parse --git-common-dir`/b-stack/), shared by all its worktrees and
kept out of .build, which check.py replaces with a link into the cache folder. They are local to that clone: a fresh
clone or another machine has none, so `audit` answers only for checks run here.

Usage:
  python3 scripts/handback.py stop             the Stop hook (reads the hook's JSON on stdin)
  python3 scripts/handback.py stamp <file>     the commit-msg hook
  python3 scripts/handback.py audit [<rev>…]   whether each commit's tree was checked (default HEAD; ranges like main~5..main)
  python3 scripts/handback.py summary          hand-back counts so far
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GATES = ['compiler', 'tuist', 'swiftlint', 'harmonize', 'tests', 'verify']


def git(root: Path, *args: str, env: dict | None = None) -> str:
    return subprocess.run(['git', *args], cwd=root, env=env, capture_output=True, text=True, check=True).stdout.strip()


def state_dir(root: Path) -> Path:
    try:
        path = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir')) / 'b-stack'
    except subprocess.CalledProcessError:
        path = root / '.build'  # not a git repo: nothing to audit, but keep the log somewhere
    path.mkdir(parents=True, exist_ok=True)
    return path


def files_tree(root: Path) -> str | None:
    """Git tree id of every tracked and untracked, non-ignored file as it is now. None outside a git repo."""
    try:
        index = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'index'))
    except subprocess.CalledProcessError:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / 'index'
        if index.is_file():
            shutil.copy2(index, scratch)  # keeps the stat cache, so only changed files are hashed
        env = {**os.environ, 'GIT_INDEX_FILE': str(scratch)}
        git(root, 'add', '-A', env=env)
        return git(root, 'write-tree', env=env)


def head_tree(root: Path) -> str | None:
    proc = subprocess.run(['git', 'rev-parse', '-q', '--verify', 'HEAD^{tree}'], cwd=root, capture_output=True, text=True)
    return proc.stdout.strip() or None


def checkout(root: Path) -> str:
    return str(Path(git(root, 'rev-parse', '--show-toplevel')).resolve())


def record_check(root: Path, gates: list[str], failed: list[str]) -> None:
    """Called by check.py after every run."""
    tree = files_tree(root)
    head = subprocess.run(['git', 'rev-parse', '--verify', '-q', 'HEAD'], cwd=root, capture_output=True, text=True)
    run = {'tree': tree, 'head': head.stdout.strip() or None, 'gates': gates, 'failed': failed,
           'checkout': checkout(root) if tree else str(root), 'time': now()}
    append(state_dir(root) / 'checks.jsonl', run)


def passed(run: dict) -> bool:
    return set(GATES) <= set(run.get('gates', [])) and not run.get('failed')


def verdict(root: Path, tree: str | None) -> tuple[str, dict]:
    """The best run on this tree: checked if any run passed every gate, partial if any ran, else unchecked."""
    runs = [r for r in entries(state_dir(root) / 'checks.jsonl') if tree and r.get('tree') == tree]
    for run in reversed(runs):
        if passed(run):
            return 'checked', run
    return ('partial', runs[-1]) if runs else ('unchecked', {})


def worktrees(root: Path) -> list[str]:
    out = git(root, 'worktree', 'list', '--porcelain')
    paths = [Path(line[9:]).resolve() for line in out.splitlines() if line.startswith('worktree ')]
    return [str(path) for path in paths if path.is_dir()]  # a deleted worktree is listed until pruned


def worked_in(root: Path, hook_input: dict) -> list[str]:
    """Checkouts of this repo the session worked in: where its hook ran, its current folder (a Claude Code worktree),
    and any other worktree its transcript names (an agent that cds into a sibling worktree)."""
    known = worktrees(root)
    found = {checkout(root)}
    cwd = hook_input.get('cwd')
    if cwd and Path(cwd).is_dir():
        try:
            found.add(checkout(Path(cwd)))
        except subprocess.CalledProcessError:
            pass
    try:
        transcript = Path(hook_input.get('transcript_path') or '').read_text(errors='replace')
    except OSError:
        transcript = ''
    found |= {path for path in known if re.search(re.escape(path) + r'(?![\w.-])', transcript)}
    return [path for path in known if path in found]


def stop(root: Path, hook_input: dict) -> list[dict]:
    log = state_dir(root) / 'handbacks.jsonl'
    history = entries(log)
    logged = []
    for path in worked_in(root, hook_input):
        tree = files_tree(Path(path))
        previous = [e for e in history if e.get('checkout') == path]
        status, run = verdict(root, tree)
        if previous and previous[-1].get('tree') == tree:
            status = 'unchanged'
        elif not previous and tree == head_tree(Path(path)):
            status = 'unchanged'  # first hand-back from a clean checkout: nothing was handed back
        entry = {'time': now(), 'status': status, 'session': hook_input.get('session_id'), 'checkout': path,
                 'tree': tree, 'gates': run.get('gates'), 'failed': run.get('failed')}
        append(log, entry)
        logged.append(entry)
    return logged


def stamp(root: Path, message_file: Path) -> None:
    message = message_file.read_text()
    if '\nChecked: ' in message:
        return
    status, run = verdict(root, git(root, 'write-tree'))  # the index being committed (git sets GIT_INDEX_FILE)
    trailer = f'Checked: {status}'
    if status == 'partial':
        trailer += f' (gates {",".join(run.get("gates", []))}; failed {",".join(run.get("failed", [])) or "none"})'
    subprocess.run(['git', 'interpret-trailers', '--in-place', '--trailer', trailer, str(message_file)], cwd=root, check=True)


def audit(root: Path, revs: list[str]) -> list[str]:
    commits = []
    for rev in revs or ['HEAD']:
        commits += git(root, 'rev-list', rev).splitlines() if '..' in rev else [git(root, 'rev-parse', '--verify', rev + '^{commit}')]
    return [f'{c[:9]} {status:9} {git(root, "log", "-1", "--format=%s", c)}{f"  ({why})" if why else ""}'
            for c in commits for status, why in [audit_commit(root, c)]]


def audit_commit(root: Path, commit: str) -> tuple[str, str]:
    tree = git(root, 'rev-parse', commit + '^{tree}')
    status, run = verdict(root, tree)
    if status == 'checked':
        return status, f'passed {run["time"]} in {run["checkout"]}'
    if status == 'partial':
        return status, f'gates {",".join(run.get("gates", []))}; failed {",".join(run.get("failed", [])) or "none"}'
    nearest = None
    for run in [r for r in entries(state_dir(root) / 'checks.jsonl') if passed(r) and r.get('tree')][-50:]:
        diff = subprocess.run(['git', 'diff', '--name-only', run['tree'], tree], cwd=root, capture_output=True, text=True)
        if diff.returncode == 0 and (nearest is None or len(diff.stdout.split()) <= len(nearest[1])):
            nearest = run, diff.stdout.split()
    if nearest is None:
        return status, 'no check passed on these files'
    run, files = nearest
    why = f'no check ran on these files; nearest passing check ({run["time"]}) differs in {len(files)} file(s): ' \
          + ', '.join(files[:5]) + (' …' if len(files) > 5 else '')
    parent = subprocess.run(['git', 'rev-parse', '-q', '--verify', commit + '^'], cwd=root, capture_output=True, text=True)
    base = parent.stdout.strip()
    if base and run.get('head') and subprocess.run(['git', 'merge-base', '--is-ancestor', base, run['head']],
                                                    cwd=root, capture_output=True).returncode == 1:
        why += f'; that check ran on a base without {base[:9]} (this commit\'s parent): main moved after it'
    return status, why


def summary(root: Path) -> str:
    counted = [e for e in entries(state_dir(root) / 'handbacks.jsonl') if e.get('status') != 'unchanged']
    counts = {s: sum(e['status'] == s for e in counted) for s in ('checked', 'partial', 'unchecked')}
    rate = f'{100 * counts["unchecked"] / len(counted):.0f}%' if counted else 'n/a'
    return f'hand-backs: {len(counted)}  checked: {counts["checked"]}  partial: {counts["partial"]}  ' \
           f'unchecked: {counts["unchecked"]}  unchecked rate: {rate}'


def entries(path: Path) -> list[dict]:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass  # a torn line from an interrupted write
    return out


def append(path: Path, entry: dict) -> None:
    with path.open('a') as log:
        log.write(json.dumps(entry) + '\n')


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'audit':  # a query, not a hook: report errors (an unknown commit) and fail
        try:
            print('\n'.join(audit(ROOT, sys.argv[2:])))
        except subprocess.CalledProcessError as error:
            sys.exit(f'handback.py audit: {error.stderr.strip() or error}')
        sys.exit(0)
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
