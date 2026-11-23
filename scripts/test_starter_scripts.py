"""Tests for the starter's Python helpers that rule cases can't reach (they run outside check.py's gates).

Covers every starter: the iOS one's check record and simulator lock, the Rust one's tool and toolchain setup, and the
TypeScript one's tool setup (Node.js, pnpm and where installed packages go). Also the skills' tools: art-eval's pick
page builder, its answer export and its planted-flaw ranking.

Usage: python3 scripts/test_starter_scripts.py
"""
from pathlib import Path
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'starters/ios/template'
RUST_TEMPLATE = ROOT / 'starters/rust/template'
TS_TEMPLATE = ROOT / 'starters/typescript/template'
sys.path.insert(0, str(TEMPLATE / 'scripts'))
import handback  # noqa: E402
import paths  # noqa: E402
import simulator  # noqa: E402
import tools  # noqa: E402
ART_EVAL = ROOT / 'skills/art-eval'
sys.path.insert(0, str(ART_EVAL / 'picks'))
sys.path.insert(0, str(ART_EVAL / 'flaws'))
import build as pick_build  # noqa: E402
import export as pick_export  # noqa: E402
import rank as flaw_rank  # noqa: E402

ENV = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.invalid',
       'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.invalid'}


class HandbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / 'scripts').mkdir()
        shutil.copy2(TEMPLATE / 'scripts/handback.py', self.root / 'scripts/handback.py')
        shutil.copytree(TEMPLATE / '.githooks', self.root / '.githooks')
        shutil.copy2(TEMPLATE / '.gitignore', self.root / '.gitignore')
        (self.root / 'App.swift').write_text('let a = 1\n')
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'core.hooksPath', '.githooks')
        self.git('add', '-A')
        self.git('commit', '-qm', 'start')
        handback.start(self.root, {'session_id': 's'})  # Claude Code's SessionStart hook

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(['git', *args], cwd=cwd or self.root, env=ENV, check=True, capture_output=True,
                              text=True).stdout

    def edit(self, text: str, name: str = 'App.swift', root: Path | None = None) -> None:
        ((root or self.root) / name).write_text(text)

    def record(self, gates: list[str], failed: list[str], root: Path | None = None) -> None:
        """A check.py run on the files as they are now."""
        root = root or self.root
        handback.record_check(root, gates, failed, handback.snapshot(root))

    def check(self, root: Path | None = None) -> None:
        self.record(handback.GATES, [], root)

    def stop(self, **hook_input: str) -> str:
        entries = handback.stop(self.root, {'session_id': 's', **hook_input})
        return {e['checkout']: e['status'] for e in entries}[str(self.root.resolve())]

    def audit(self, rev: str = 'HEAD') -> str:
        return subprocess.run([sys.executable, str(self.root / 'scripts/handback.py'), 'audit', rev],
                              cwd=self.root, capture_output=True, text=True).stdout

    def feature_branch(self) -> None:
        self.git('checkout', '-qb', 'feature')
        self.edit('let a = 2\n')
        self.check()
        self.git('commit', '-qam', 'Change a')
        self.git('checkout', '-q', 'main')

    def squash_merge(self) -> None:
        """Like GitHub's squash merge: one new commit with the branch's changes, no local hooks, no trailers."""
        self.git('merge', '--squash', '-q', 'feature')
        self.git('commit', '-q', '--no-verify', '-m', 'Change a (#1)')

    def test_clean_repo_without_edits_is_unchanged(self) -> None:
        self.assertEqual(self.stop(), 'unchanged')

    def test_edit_without_a_check_is_unchecked(self) -> None:
        self.edit('let a = 2\n')
        self.assertEqual(self.stop(), 'unchecked')

    def test_full_passing_check_on_the_same_files_is_checked(self) -> None:
        self.edit('let a = 2\n')
        self.check()
        self.assertEqual(self.stop(), 'checked')

    def test_skipped_or_failed_gate_is_partial(self) -> None:
        self.edit('let a = 2\n')
        self.record(['compiler', 'swiftlint'], [])
        self.assertEqual(self.stop(), 'partial')
        self.edit('let a = 3\n')
        self.record(handback.GATES, ['verify'])
        self.assertEqual(self.stop(), 'partial')

    def test_edit_after_the_check_is_unchecked(self) -> None:
        self.check()
        self.edit('let a = 2\n')
        self.assertEqual(self.stop(), 'unchecked')

    def test_new_untracked_file_counts_as_an_edit(self) -> None:
        self.check()
        (self.root / 'New.swift').write_text('let b = 1\n')
        self.assertEqual(self.stop(), 'unchecked')

    def test_no_new_edits_since_last_handback_is_unchanged(self) -> None:
        self.edit('let a = 2\n')
        self.assertEqual(self.stop(), 'unchecked')
        self.assertEqual(self.stop(), 'unchanged')

    def test_build_output_is_not_an_edit(self) -> None:
        self.check()
        (self.root / '.build').mkdir()
        (self.root / '.build' / 'log.txt').write_text('x')
        self.assertEqual(handback.verdict(self.root, handback.files_tree(self.root))[0], 'checked')

    def test_summary_leaves_out_unchanged(self) -> None:
        self.stop()
        self.edit('let a = 2\n')
        self.stop()
        self.check()
        self.edit('let a = 3\n')
        self.check()
        self.stop()
        self.assertEqual(handback.summary(self.root),
                         'hand-backs: 2  checked: 1  partial: 0  unchecked: 1  unchecked rate: 50%')
        lines = (handback.state_dir(self.root) / 'handbacks.jsonl').read_text().splitlines()
        self.assertEqual([json.loads(line)['status'] for line in lines], ['start', 'unchanged', 'unchecked', 'checked'])

    def test_commit_hook_stamps_unchecked_commit(self) -> None:
        self.edit('let a = 2\n')
        self.git('commit', '-qam', 'Change a')
        self.assertIn('Checked: unchecked', self.git('log', '-1', '--format=%B'))

    def test_commit_hook_stamps_checked_commit_and_keeps_other_trailers(self) -> None:
        self.edit('let a = 2\n')
        self.check()
        self.git('commit', '-qam', 'Change a\n\nBody.\n\nCo-Authored-By: x <x@example.invalid>')
        trailers = self.git('log', '-1', '--format=%(trailers)')
        self.assertIn('Checked: checked', trailers)
        self.assertIn('Co-Authored-By: x', trailers)

    def test_commit_hook_stamps_the_staged_files_not_the_working_ones(self) -> None:
        self.edit('let a = 2\n')
        self.edit('let b = 1\n', 'Scratch.swift')  # work the commit leaves out
        self.check()
        self.git('commit', '-qm', 'Change a', 'App.swift')
        self.assertIn('Checked: unchecked', self.git('log', '-1', '--format=%B'))  # the check also had Scratch.swift

    def test_amend_replaces_the_trailer(self) -> None:
        self.edit('let a = 2\n')
        self.check()
        self.git('commit', '-qam', 'Change a')
        self.edit('let a = 3\n')
        self.git('commit', '-qa', '--amend', '--no-edit')
        message = self.git('log', '-1', '--format=%B')
        self.assertIn('Checked: unchecked', message)
        self.assertNotIn('Checked: checked', message)

    def test_commit_before_the_first_hand_back_is_still_a_hand_back(self) -> None:
        self.edit('let a = 2\n')
        self.git('commit', '-qam', 'Change a')  # the checkout is clean again at the Stop
        self.assertEqual(self.stop(), 'unchecked')

    def test_a_session_started_meanwhile_does_not_hide_a_hand_back(self) -> None:
        self.edit('let a = 2\n')
        self.git('commit', '-qam', 'Change a')
        handback.start(self.root, {'session_id': 'other'})  # a parallel session starts on the edited files
        self.assertEqual(self.stop(), 'unchecked')

    def test_files_changed_while_check_py_ran_are_not_recorded(self) -> None:
        before = handback.snapshot(self.root)
        self.edit('let a = 2\n')  # an edit while the gates run: earlier gates never saw it
        handback.record_check(self.root, handback.GATES, [], before)
        self.assertEqual(self.stop(), 'unchecked')
        self.git('commit', '-qam', 'Change a')
        self.assertRegex(self.audit(), r'^[0-9a-f]{9} unchecked ')

    # The audit trail follows the code (F6, F8 in the hexfleet trial).

    def test_squash_merge_of_a_checked_branch_audits_checked(self) -> None:
        self.feature_branch()
        self.squash_merge()
        self.assertNotIn('Checked:', self.git('log', '-1', '--format=%B'))
        self.assertRegex(self.audit(), r'^[0-9a-f]{9} checked ')

    def test_check_after_the_commit_audits_checked(self) -> None:
        self.edit('let a = 2\n')
        self.git('commit', '-qam', 'Change a')
        self.check()
        self.assertRegex(self.audit(), r'^[0-9a-f]{9} checked ')

    def test_edit_after_the_check_then_commit_audits_unchecked(self) -> None:
        self.check()
        self.edit('let a = 2\n')
        self.git('commit', '-qam', 'Change a')
        self.assertRegex(self.audit(), r'^[0-9a-f]{9} unchecked .*differs in 1 file\(s\): App\.swift')

    def test_squash_merge_after_main_moved_audits_unchecked_and_says_why(self) -> None:
        self.feature_branch()
        self.edit('let c = 1\n', 'Other.swift')
        self.git('add', 'Other.swift')
        self.git('commit', '-qm', 'Meanwhile on main')
        self.squash_merge()
        self.assertRegex(self.audit(), r'^[0-9a-f]{9} unchecked .*Other\.swift.*main moved after it')
        self.assertRegex(self.audit('HEAD~1'), r'^[0-9a-f]{9} unchecked ')
        self.assertRegex(self.audit('feature'), r'^[0-9a-f]{9} checked ')

    def test_audit_of_an_unknown_commit_fails(self) -> None:
        proc = subprocess.run([sys.executable, str(self.root / 'scripts/handback.py'), 'audit', 'nope'],
                              cwd=self.root, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)

    # Where hand-backs are logged (F7 in the hexfleet trial).

    def test_log_survives_check_py_linking_build_into_the_cache(self) -> None:
        (self.root / '.build').mkdir()  # a real .build, as left by anything that ran before check.py
        self.edit('let a = 2\n')
        self.stop()
        cache = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, cache)
        with mock.patch.dict(os.environ, {'BSTACK_CACHE_DIR': str(cache)}):
            paths.link_build_dirs(self.root)  # what check.py does first
        self.assertTrue((self.root / '.build').is_symlink())
        self.assertEqual(handback.summary(self.root),
                         'hand-backs: 1  checked: 0  partial: 0  unchecked: 1  unchecked rate: 100%')

    def test_hand_back_from_a_sibling_worktree_named_in_the_transcript_is_logged(self) -> None:
        sibling = self.root.parent / (self.root.name + '-feature')
        self.addCleanup(shutil.rmtree, sibling, True)
        self.git('worktree', 'add', '-qb', 'feature', str(sibling))
        transcript = self.root / '.build/transcript.jsonl'
        transcript.parent.mkdir()
        transcript.write_text(json.dumps({'command': f'cd {sibling.resolve()} && echo x >> App.swift'}))
        self.edit('let a = 2\n', root=sibling)
        entries = handback.stop(self.root, {'session_id': 's', 'cwd': str(self.root), 'transcript_path': str(transcript)})
        self.assertEqual({e['checkout']: e['status'] for e in entries},
                         {str(self.root.resolve()): 'unchanged', str(sibling.resolve()): 'unchecked'})
        self.check(sibling)
        self.edit('let a = 2\n', root=sibling)
        entries = handback.stop(self.root, {'session_id': 's', 'transcript_path': str(transcript)})
        self.assertEqual([e['status'] for e in entries if e['checkout'] == str(sibling.resolve())], ['unchanged'])
        self.edit('let a = 3\n', root=sibling)
        self.check(sibling)
        entries = handback.stop(self.root, {'session_id': 's', 'transcript_path': str(transcript)})
        self.assertEqual([e['status'] for e in entries if e['checkout'] == str(sibling.resolve())], ['checked'])

    def test_hand_back_from_a_claude_code_worktree_is_logged_and_ignored_by_the_main_checkout(self) -> None:
        nested = self.root / '.claude/worktrees/probe'
        self.git('worktree', 'add', '-qb', 'probe', str(nested))
        self.edit('let a = 2\n', root=nested)
        entries = handback.stop(self.root, {'session_id': 's', 'cwd': str(nested)})
        self.assertEqual({e['checkout']: e['status'] for e in entries},
                         {str(self.root.resolve()): 'unchanged', str(nested.resolve()): 'unchecked'})

    def test_commit_hook_never_blocks(self) -> None:
        (self.root / 'scripts/handback.py').write_text('raise SystemExit(3)\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'Break the helper')  # would raise CalledProcessError if the hook blocked

    def test_stop_hook_never_fails_on_bad_input(self) -> None:
        proc = subprocess.run([sys.executable, str(self.root / 'scripts/handback.py'), 'stop'],
                              cwd=self.root, input='not json', capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)


HOLD = """
import sys
sys.path.insert(0, sys.argv[1])
from simulator import in_use
with in_use(sys.argv[2], sys.argv[3]):
    print('holding', flush=True)
    sys.stdin.read()  # until the test closes stdin (or kills this process)
print('released', flush=True)
"""


class SimulatorProcesses(unittest.TestCase):
    """Processes holding simulator locks in a scratch home folder, stopped after each test."""

    def setUp(self) -> None:
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home)
        self.env = {**os.environ, 'HOME': str(home)}
        self.env.pop(simulator.HELD, None)
        self.procs: list[subprocess.Popen] = []
        self.addCleanup(self.stop_all)

    def stop_all(self) -> None:
        for proc in self.procs:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            for stream in (proc.stdin, proc.stdout):
                if stream:
                    stream.close()

    def hold(self, udid: str, holder: str, env: dict | None = None) -> subprocess.Popen:
        proc = subprocess.Popen([sys.executable, '-c', HOLD, str(TEMPLATE / 'scripts'), udid, holder],
                                env=env or self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.procs.append(proc)
        return proc

    def line(self, proc: subprocess.Popen) -> str:
        return proc.stdout.readline().strip()


class SimulatorLockTests(SimulatorProcesses):
    """Two checkouts' gates on one simulator kill each other's test runner, so in_use() makes the second wait."""

    def test_second_holder_waits_and_says_who_holds_it(self) -> None:
        first = self.hold('SIM-1', 'check.py in /checkouts/a')
        self.assertEqual(self.line(first), 'holding')
        second = self.hold('SIM-1', 'check.py in /checkouts/b')
        waiting = self.line(second)
        self.assertIn('[simulator] waiting for simulator SIM-1: in use by '
                      f'pid {first.pid}, check.py in /checkouts/a, since ', waiting)
        time.sleep(0.5)
        self.assertIsNone(second.poll())  # still waiting
        first.stdin.close()
        self.assertEqual(self.line(first), 'released')
        self.assertRegex(self.line(second), r'^\[simulator\] got simulator SIM-1 after \d+s$')
        self.assertEqual(self.line(second), 'holding')

    def test_killed_holder_releases_the_lock(self) -> None:
        first = self.hold('SIM-1', 'check.py in /checkouts/a')
        self.assertEqual(self.line(first), 'holding')
        second = self.hold('SIM-1', 'check.py in /checkouts/b')
        self.assertIn('waiting for simulator SIM-1', self.line(second))
        first.kill()
        self.assertIn('got simulator SIM-1', self.line(second))
        self.assertEqual(self.line(second), 'holding')

    def test_a_waiting_gate_thread_stops_on_ctrl_c(self) -> None:
        """check.py waits in a worker thread, which Ctrl-C doesn't reach; its STOP event must end the wait."""
        self.assertEqual(self.line(self.hold('SIM-1', 'a')), 'holding')
        stop = threading.Event()
        threading.Timer(1.5, stop.set).start()
        with mock.patch.dict(os.environ, {'HOME': self.env['HOME']}), self.assertRaises(KeyboardInterrupt):
            with simulator.in_use('SIM-1', 'b', stop):
                self.fail('took a lock another process holds')

    def test_other_simulators_do_not_wait(self) -> None:
        self.assertEqual(self.line(self.hold('SIM-1', 'a')), 'holding')
        self.assertEqual(self.line(self.hold('SIM-2', 'b')), 'holding')

    def test_a_child_of_the_holder_does_not_wait_for_it(self) -> None:
        """check.py holds the lock and runs verify.py, and test_rules.py holds it and runs check.py: neither child
        may wait for its parent's lock, or the gate deadlocks."""
        first = self.hold('SIM-1', 'test_rules.py on /checkouts/a')
        self.assertEqual(self.line(first), 'holding')
        nested = {**self.env, simulator.HELD: 'SIM-2,SIM-1'}  # what in_use yields for the parent to pass on
        child = self.hold('SIM-1', 'check.py in /work/w0', nested)
        self.assertEqual(self.line(child), 'holding')
        grandchild = self.hold('SIM-1', 'verify.py in /work/w0', nested)
        self.assertEqual(self.line(grandchild), 'holding')
        outsider = self.hold('SIM-1', 'check.py in /checkouts/b')
        self.assertIn(f'in use by pid {first.pid}, test_rules.py on /checkouts/a', self.line(outsider))

    def test_yields_the_environment_that_marks_the_lock_held(self) -> None:
        with mock.patch.dict(os.environ, {'HOME': self.env['HOME'], simulator.HELD: 'SIM-0'}):
            with simulator.in_use('SIM-1', 'test') as env:
                self.assertEqual(env, {simulator.HELD: 'SIM-0,SIM-1'})
                with mock.patch.dict(os.environ, env):
                    with simulator.in_use('SIM-1', 'nested') as inner:  # would block forever if it took the lock again
                        self.assertEqual(inner, env)


class RustToolsTests(unittest.TestCase):
    """The Rust starter's scripts/tools.py, run in a copy of the starter's scripts with a temporary tools folder."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()  # tools.py resolves its own path (/var is /private/var)
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(RUST_TEMPLATE / 'scripts', self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy2(RUST_TEMPLATE / 'rust-toolchain.toml', self.root / 'rust-toolchain.toml')
        self.tools = self.root / 'tools'
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        self.env = {**os.environ, 'BSTACK_TOOLS_DIR': str(self.tools), 'BSTACK_CACHE_DIR': str(self.cache)}

    def run_tools(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / 'scripts/tools.py'), *args], env=self.env,
                              capture_output=True, text=True)

    def pin(self, archive: Path, sha256: str) -> None:
        (self.root / 'tools.toml').write_text(
            f'[fake]\nversion = "1.0"\nurl = "{archive.as_uri()}"\nsha256 = "{sha256}"\nbinary = "fake-1.0/fake"\n')

    def fake_archive(self) -> Path:
        source = self.root / 'src/fake-1.0'
        source.mkdir(parents=True)
        (source / 'fake').write_text('#!/bin/sh\necho fake\n')
        archive = self.root / 'fake-1.0.tar.gz'
        subprocess.run(['tar', 'czf', str(archive), '-C', str(source.parent), 'fake-1.0'], check=True)
        return archive

    def test_tar_gz_tool_is_verified_unpacked_and_runnable(self) -> None:
        archive = self.fake_archive()
        self.pin(archive, hashlib.sha256(archive.read_bytes()).hexdigest())
        result = self.run_tools('fake')
        self.assertEqual(result.returncode, 0, result.stderr)
        binary = Path(result.stdout.strip())
        self.assertEqual(binary, self.tools / 'fake-1.0/fake-1.0/fake')
        self.assertEqual(subprocess.run([str(binary)], capture_output=True, text=True).stdout, 'fake\n')

    def test_checksum_mismatch_is_refused_and_leaves_nothing(self) -> None:
        self.pin(self.fake_archive(), '0' * 64)
        result = self.run_tools('fake')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stderr)
        self.assertFalse((self.tools / 'fake-1.0').exists())

    def test_rust_env_keeps_toolchain_and_build_output_out_of_home(self) -> None:
        # A toolchain already in the tools folder, so nothing is downloaded.
        toolchain = self.tools / 'rust/rustup/toolchains/1.99.0-aarch64-apple-darwin'
        (toolchain / 'bin').mkdir(parents=True)
        (toolchain / 'bin/cargo-clippy').write_text('')
        script = ('import json, sys; sys.path.insert(0, sys.argv[1]); from tools import rust_env; '
                  'print(json.dumps(rust_env()))')
        result = subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts')], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        env = json.loads(result.stdout)
        self.assertEqual(env['RUSTUP_HOME'], str(self.tools / 'rust/rustup'))
        self.assertEqual(env['CARGO_HOME'], str(self.tools / 'rust/cargo'))
        self.assertEqual(env['RUSTUP_TOOLCHAIN'], '1.99.0')
        self.assertEqual(env['PATH'].split(os.pathsep)[0], str(toolchain / 'bin'))
        self.assertEqual(env['CARGO_TARGET_DIR'], str(self.root / '.build/target'))
        self.assertEqual(env['RUSTFLAGS'], '-D warnings')
        # .build is a link into the cache folder, so build output lands there.
        self.assertTrue((self.root / '.build').is_symlink())
        self.assertTrue((self.root / '.build').resolve().is_relative_to(self.cache.resolve()))
        if Path('/usr/bin/cc').is_file():
            self.assertEqual(env['CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER'], '/usr/bin/cc')

    def test_missing_cache_drive_stops_instead_of_building_elsewhere(self) -> None:
        self.env['BSTACK_CACHE_DIR'] = str(self.root / 'unmounted')
        self.env.pop('BSTACK_TOOLS_DIR')
        result = self.run_tools('rust')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Is its drive mounted?', result.stderr)
        self.assertFalse((self.root / '.build').exists())

    def test_paths_helper_matches_the_ios_starter(self) -> None:
        # One cache-folder policy for every starter: a change to one copy must be made to both.
        self.assertEqual((RUST_TEMPLATE / 'scripts/paths.py').read_text(), (TEMPLATE / 'scripts/paths.py').read_text())


class TypeScriptToolsTests(unittest.TestCase):
    """The TypeScript starter's scripts/tools.py, in a copy of its scripts with fake Node.js and pnpm archives."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(TS_TEMPLATE / 'scripts', self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        self.tools = self.root / 'tools'
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        self.env = {**os.environ, 'BSTACK_TOOLS_DIR': str(self.tools), 'BSTACK_CACHE_DIR': str(self.cache)}

    def archive(self, name: str) -> tuple[Path, str]:
        source = self.root / f'src/{name}/bin'
        source.mkdir(parents=True)
        (source / name).write_text(f'#!/bin/sh\necho {name}\n')
        archive = self.root / f'{name}.tar.gz'
        subprocess.run(['tar', 'czf', str(archive), '-C', str(self.root / 'src'), name], check=True)
        return archive, hashlib.sha256(archive.read_bytes()).hexdigest()

    def pin(self, node_sha: str | None = None) -> None:
        node, node_digest = self.archive('node')
        pnpm, pnpm_digest = self.archive('pnpm')
        (self.root / 'tools.toml').write_text(
            f'[node]\nversion = "1.0"\nurl = "{node.as_uri()}"\nsha256 = "{node_sha or node_digest}"\nbinary = "node/bin/node"\n'
            f'[pnpm]\nversion = "1.0"\nurl = "{pnpm.as_uri()}"\nsha256 = "{pnpm_digest}"\nbinary = "pnpm/bin/pnpm"\n')

    def node_env(self) -> subprocess.CompletedProcess:
        script = ('import json, sys; sys.path.insert(0, sys.argv[1]); from tools import node_env; '
                  'print(json.dumps(node_env()))')
        return subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts')], env=self.env,
                              capture_output=True, text=True)

    def test_node_env_puts_pinned_tools_first_and_installs_in_the_cache(self) -> None:
        self.pin()
        result = self.node_env()
        self.assertEqual(result.returncode, 0, result.stderr)
        env = json.loads(result.stdout)
        path = env['PATH'].split(os.pathsep)
        self.assertEqual(path[:3], [str(self.root / 'node_modules/.bin'), str(self.tools / 'node-1.0/node/bin'),
                                    str(self.tools / 'pnpm-1.0/pnpm/bin')])
        self.assertEqual(env['pnpm_config_store_dir'], str(self.tools / 'pnpm-store'))
        self.assertTrue(Path(env['pnpm_config_virtual_store_dir']).is_relative_to(self.cache))
        self.assertEqual(env['electron_config_cache'], str(self.tools / 'electron-cache'))
        self.assertTrue((self.root / '.build').resolve().is_relative_to(self.cache.resolve()))

    def test_node_env_drops_inherited_package_manager_settings(self) -> None:
        self.pin()
        self.env['npm_config_registry'] = 'https://example.invalid/'
        self.env['pnpm_config_registry'] = 'https://example.invalid/'
        env = json.loads(self.node_env().stdout)
        self.assertNotIn('npm_config_registry', env)
        self.assertNotIn('pnpm_config_registry', env)

    def test_checksum_mismatch_is_refused_and_leaves_nothing(self) -> None:
        self.pin(node_sha='0' * 64)
        result = self.node_env()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stderr)
        self.assertFalse((self.tools / 'node-1.0').exists())

    def test_missing_cache_drive_stops_instead_of_installing_elsewhere(self) -> None:
        self.pin()
        self.env['BSTACK_CACHE_DIR'] = str(self.root / 'unmounted')
        result = self.node_env()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Is its drive mounted?', result.stderr)
        self.assertFalse((self.root / '.build').exists())

    def test_paths_helper_matches_the_ios_starter(self) -> None:
        self.assertEqual((TS_TEMPLATE / 'scripts/paths.py').read_text(), (TEMPLATE / 'scripts/paths.py').read_text())

    def test_handback_helper_matches_the_ios_starter_but_its_gates(self) -> None:
        # One check record for every starter that has it: only the gate list may differ.
        strip = lambda text: [line for line in text.splitlines() if not line.startswith('GATES = ')]
        self.assertEqual(strip((TS_TEMPLATE / 'scripts/handback.py').read_text()),
                         strip((TEMPLATE / 'scripts/handback.py').read_text()))
        gates = next(l for l in (TS_TEMPLATE / 'scripts/handback.py').read_text().splitlines() if l.startswith('GATES = '))
        self.assertIn(gates.split(' = ', 1)[1], (TS_TEMPLATE / 'scripts/check.py').read_text())


class NewFeatureTests(unittest.TestCase):
    """The TypeScript starter's scripts/new_feature.py, in a copy of its scripts and module shape."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(TS_TEMPLATE / 'scripts', self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        (self.root / 'arch').mkdir()
        shutil.copy2(TS_TEMPLATE / 'arch/shape.json', self.root / 'arch/shape.json')

    def run_new(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / 'scripts/new_feature.py'), *args], capture_output=True,
                              text=True)

    def test_creates_the_package_map_entry_and_journey(self) -> None:
        result = self.run_new('daily-notes')
        self.assertEqual(result.returncode, 0, result.stderr)
        package = json.loads((self.root / 'packages/features/daily-notes/package.json').read_text())
        self.assertEqual(package['name'], '@app/daily-notes')
        self.assertEqual(json.loads((self.root / 'packages/features/daily-notes/tsconfig.json').read_text()),
                         {'extends': '../../../arch/tsconfig/feature.json'})
        self.assertIn('modules = ["daily-notes"]', (self.root / 'feature-map/daily-notes.toml').read_text())
        self.assertIn('name = "daily_notes_works"', (self.root / 'feature-map/daily-notes.toml').read_text())
        journey = (self.root / 'apps/desktop/journeys/daily-notes.journey.ts').read_text()
        self.assertIn('test("daily_notes_works"', journey)
        self.assertIn('expect.unreachable("Write this journey', journey)
        self.assertIn('expect.unreachable("Write this test',
                      (self.root / 'packages/features/daily-notes/tests/daily-notes.test.ts').read_text())

    def test_refuses_a_bad_name_and_an_existing_feature(self) -> None:
        self.assertEqual(self.run_new('Notes').returncode, 2)
        self.assertEqual(self.run_new('two words').returncode, 2)
        self.assertEqual(self.run_new('notes').returncode, 0)
        again = self.run_new('notes')
        self.assertEqual(again.returncode, 1)
        self.assertIn('already exist', again.stderr)


class HandUseTests(SimulatorProcesses):
    """Driving the simulator by hand (recordings, agent-device) goes through `simulator.py run`, which takes the same
    lock, so a gate from another checkout never runs journeys while someone else's app is in front."""

    def hand(self, *args: str) -> subprocess.Popen:
        proc = subprocess.Popen([sys.executable, str(TEMPLATE / 'scripts/simulator.py'), 'run', *args],
                                env={**self.env, 'BSTACK_SIMULATOR_ID': 'SIM-1'}, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True)
        self.procs.append(proc)
        return proc

    def test_waits_for_a_held_simulator_then_runs_and_releases_it(self) -> None:
        gate = self.hold('SIM-1', 'check.py in /checkouts/a')
        self.assertEqual(self.line(gate), 'holding')
        hand = self.hand('--', sys.executable, '-c',
                         'import os; print("ran on", os.environ["BSTACK_SIMULATOR_ID"], os.environ["BSTACK_SIMULATOR_LOCKS"])')
        self.assertIn(f'waiting for simulator SIM-1: in use by pid {gate.pid}, check.py in /checkouts/a', self.line(hand))
        time.sleep(0.5)
        self.assertIsNone(hand.poll())  # the command hasn't run
        gate.stdin.close()
        self.assertIn('got simulator SIM-1', self.line(hand))
        self.assertIn('[simulator] holding simulator SIM-1 for: ', self.line(hand))
        self.assertEqual(self.line(hand), 'ran on SIM-1 SIM-1')  # nested scripts (verify.py launch) won't wait for it
        self.assertEqual(self.line(hand), '[simulator] released simulator SIM-1')
        self.assertEqual(hand.wait(), 0)
        self.assertEqual(self.line(self.hold('SIM-1', 'check.py in /checkouts/b')), 'holding')

    def test_a_gate_waits_while_the_hand_command_runs(self) -> None:
        hand = self.hand('--', sys.executable, '-c', 'import sys; print("recording", flush=True); sys.stdin.read()')
        self.assertIn('holding simulator SIM-1', self.line(hand))
        self.assertEqual(self.line(hand), 'recording')
        gate = self.hold('SIM-1', 'check.py in /checkouts/b')
        self.assertIn(f'in use by pid {hand.pid}, simulator.py run in {TEMPLATE}: ', self.line(gate))
        hand.stdin.close()  # the command ends
        self.assertIn('got simulator SIM-1', self.line(gate))
        self.assertEqual(self.line(gate), 'holding')
        self.assertEqual(hand.wait(), 0)

    def test_for_interrupts_the_command_like_ctrl_c(self) -> None:
        """A screen recording only writes its file when interrupted, so --for sends SIGINT, to a shell's children too."""
        started = time.monotonic()
        hand = self.hand('--for', '1', '--', 'sh', '-c', shlex.join([sys.executable, '-c', INTERRUPTIBLE]))
        self.assertIn('holding simulator SIM-1', self.line(hand))
        self.assertEqual(self.line(hand), 'interrupted')
        self.assertEqual(hand.wait(), 0)
        self.assertLess(time.monotonic() - started, 10)

    def test_nothing_the_command_started_outlives_the_hold(self) -> None:
        """A shell's background job ignores Ctrl-C; left running it would keep driving the simulator after release."""
        stopped = Path(self.env['HOME']) / 'stopped'
        job = shlex.join([sys.executable, '-c', SLOW_TO_STOP, str(stopped)])
        hand = self.hand('--for', '1', '--', 'sh', '-c', f'{job} & wait')
        self.assertIn('holding simulator SIM-1', self.line(hand))
        while (line := self.line(hand)) != 'started':  # the rest of the echoed (multi-line) command
            self.assertNotIn('released', line)
        self.assertEqual(self.line(hand), '[simulator] released simulator SIM-1')
        self.assertTrue(stopped.is_file(), 'released the simulator before the background job had stopped')
        hand.wait()

    def test_a_job_that_ignores_termination_is_killed_before_release(self) -> None:
        job = shlex.join([sys.executable, '-c', IGNORES_TERM])
        hand = self.hand('--for', '1', '--', 'sh', '-c', f'{job} & wait')
        self.assertIn('holding simulator SIM-1', self.line(hand))
        while not (line := self.line(hand)).isdigit():  # the rest of the echoed (multi-line) command
            self.assertNotIn('released', line)
        self.assertEqual(self.line(hand), '[simulator] released simulator SIM-1')
        with self.assertRaises(ProcessLookupError):
            os.kill(int(line), 0)
        hand.wait()

    def test_exit_status_is_the_commands(self) -> None:
        self.assertEqual(self.hand('--', sys.executable, '-c', 'raise SystemExit(3)').wait(), 3)


SLOW_TO_STOP = ('import pathlib, signal, sys, time\n'
                'def stop(*_):\n'
                '    time.sleep(1)\n'
                '    pathlib.Path(sys.argv[1]).write_text("stopped")\n'
                '    sys.exit(0)\n'
                'signal.signal(signal.SIGTERM, stop)\n'
                'print("started", flush=True)\n'
                'time.sleep(60)\n')
IGNORES_TERM = ('import os, signal, time\n'
                'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                'print(os.getpid(), flush=True)\n'
                'time.sleep(60)\n')
INTERRUPTIBLE = ('import signal, sys; signal.signal(signal.SIGINT, lambda *_: (print("interrupted", flush=True), '
                 'sys.exit(0))); signal.pause()')


class CheckoutBundleIdTests(unittest.TestCase):
    """Parallel checkouts of one app share simulators: each installs AppVerify and its UI-test runner under its own
    bundle ID (Project.swift), so one checkout's install never replaces another's. The shipped app keeps its ID."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tuist = str(tools.tool_path('tuist'))

    def checkout(self) -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        shutil.copy2(TEMPLATE / 'Project.swift', root)
        shutil.copy2(TEMPLATE / 'Tuist.swift', root)
        shutil.copytree(TEMPLATE / 'Tuist', root / 'Tuist', ignore=shutil.ignore_patterns('.build'))
        return root

    def bundle_ids(self, root: Path) -> dict[str, str]:
        proc = subprocess.run([self.tuist, 'dump', 'project'], cwd=root, capture_output=True, text=True,
                              env={**os.environ, 'TUIST_STATS_OPT_OUT': '1', 'TUIST_DISABLE_ANALYTICS': '1'})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return {t['name']: t['bundleId'] for t in json.loads(proc.stdout)['targets']}

    def test_each_checkout_installs_its_own_verify_apps_and_the_app_keeps_its_id(self) -> None:
        first, second = self.checkout(), self.checkout()
        a, b = self.bundle_ids(first), self.bundle_ids(second)
        for target in ('AppVerify', 'AppVerifyUITests'):
            self.assertNotEqual(a[target], b[target], target)
        self.assertRegex(a['AppVerify'], r'^dev\.bstack\.starter\.verify\.c[0-9a-f]{8}$')
        self.assertRegex(a['AppVerifyUITests'], r'^dev\.bstack\.starter\.verifyuitests\.c[0-9a-f]{8}$')
        self.assertEqual(a['App'], 'dev.bstack.starter')
        self.assertEqual(b['App'], 'dev.bstack.starter')
        self.assertEqual(self.bundle_ids(first), a)  # the same checkout keeps its IDs


try:
    from PIL import Image
except ImportError:  # only the animation strips need Pillow
    Image = None


class PickPageTests(unittest.TestCase):
    """art-eval's blind pick page: pairs in, page and images out, sides fixed per pair."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / 'sprites').mkdir()
        for name in ('a.png', 'b.png', 'c.svg'):
            (self.root / 'sprites' / name).write_bytes(f'image {name}'.encode())

    def config(self, extra: str = '', key: str = 'sprites') -> Path:
        path = self.root / 'picks.toml'
        path.write_text(f'title = "Hexfleet Picks"\n\n[[lane]]\nkey = "{key}"\nname = "Ship sprites"\n'
                        f'question = "Which sprite?"\npairs = "sprites/pairs.json"\n{extra}')
        return path

    def pairs(self, pairs: list[dict]) -> None:
        (self.root / 'sprites/pairs.json').write_text(json.dumps(pairs))

    def build(self, config: Path | None = None) -> list[dict]:
        out = self.root / 'out'
        pick_build.build(config or self.config(), out)
        page = (out / 'index.html').read_text()
        return json.loads(page.split('const LANES = ', 1)[1].split(';\n', 1)[0])

    def test_pairs_become_a_page_with_copied_images(self) -> None:
        self.pairs([{'id': 'p1', 'title': 'Interceptor', 'note': 'design', 'x': 'a.png',
                     'y': str(self.root / 'sprites/c.svg')}])
        lanes = self.build()
        page = (self.root / 'out/index.html').read_text()
        self.assertIn('<title>Hexfleet Picks</title>', page)
        self.assertNotIn('__TITLE__', page)
        [lane] = lanes
        self.assertEqual((lane['key'], lane['name'], lane['question']), ('sprites', 'Ship sprites', 'Which sprite?'))
        [pair] = lane['pairs']
        self.assertEqual((pair['id'], pair['title'], pair['note']), ('p1', 'Interceptor', 'design'))
        self.assertIn(pair['left'], ('x', 'y'))
        self.assertEqual((self.root / 'out' / pair['x']).read_bytes(), b'image a.png')
        self.assertEqual((self.root / 'out' / pair['y']).read_bytes(), b'image c.svg')
        self.assertTrue(pair['y'].startswith('img/sprites-') and pair['y'].endswith('.svg'))

    def test_sides_are_fixed_per_pair_and_mixed_across_pairs(self) -> None:
        ids = [f'p{i}' for i in range(40)]
        self.pairs([{'id': i, 'x': 'a.png', 'y': 'b.png'} for i in ids])
        first = {p['id']: p['left'] for p in self.build()[0]['pairs']}
        self.pairs([{'id': i, 'x': 'a.png', 'y': 'b.png'} for i in reversed(ids)])
        again = {p['id']: p['left'] for p in self.build()[0]['pairs']}
        self.assertEqual(first, again)
        self.assertEqual(first, {i: pick_build.side('sprites', i) for i in ids})
        self.assertTrue(10 <= list(first.values()).count('x') <= 30, first)
        other = {i: pick_build.side('icons', i) for i in ids}
        self.assertNotEqual(first, other)  # the lane is part of the hash

    def test_skip_leaves_out_pairs_by_id_prefix(self) -> None:
        self.pairs([{'id': i, 'x': 'a.png', 'y': 'b.png'} for i in ('old-1', 'old-2', 'new-1')])
        lanes = self.build(self.config('skip = ["old-"]\n'))
        self.assertEqual([p['id'] for p in lanes[0]['pairs']], ['new-1'])

    def test_lane_options_reach_the_page_and_paths_do_not(self) -> None:
        self.pairs([])
        [lane] = self.build(self.config('layout = "stack"\nsizes = [96, 24]\nhow = "At 24 px."\n'))
        self.assertEqual((lane['layout'], lane['sizes'], lane['how']), ('stack', [96, 24], 'At 24 px.'))
        self.assertNotIn('pairs.json', json.dumps(lane))

    def test_lane_without_a_pairs_file_has_no_pairs(self) -> None:
        self.assertEqual(self.build()[0]['pairs'], [])

    def test_text_cannot_close_the_script(self) -> None:
        self.pairs([{'id': 'p1', 'note': '</script><b>', 'x': 'a.png', 'y': 'b.png'}])
        self.assertEqual(self.build()[0]['pairs'][0]['note'], '</script><b>')
        self.assertEqual((self.root / 'out/index.html').read_text().count('</script>'), 1)

    def test_bad_input_is_refused(self) -> None:
        cases = {
            'pair id': [{'id': 'a/b', 'x': 'a.png', 'y': 'b.png'}],
            'used twice': [{'id': 'p', 'x': 'a.png', 'y': 'b.png'}, {'id': 'p', 'x': 'a.png', 'y': 'b.png'}],
            'not an image file': [{'id': 'p', 'x': 'a.png', 'y': 'missing.png'}],
            'has no "y"': [{'id': 'p', 'x': 'a.png'}],
        }
        for message, pairs in cases.items():
            self.pairs(pairs)
            with self.subTest(message), self.assertRaisesRegex(pick_build.ConfigError, message):
                self.build()
        with self.assertRaisesRegex(pick_build.ConfigError, 'lane key'):
            self.build(self.config(key='my__lane'))

    @unittest.skipIf(Image is None, 'needs Pillow')
    def test_animations_become_frame_strips(self) -> None:
        frames = [Image.new('RGBA', (8, 6), (40 * i, 0, 0, 255)) for i in range(3)]
        frames[0].save(self.root / 'sprites/anim.gif', save_all=True, append_images=frames[1:], duration=100, loop=0)
        frames[0].save(self.root / 'sprites/still.gif')
        self.pairs([{'id': 'p1', 'x': 'anim.gif', 'y': 'still.gif'}])
        [pair] = self.build()[0]['pairs']
        self.assertEqual(pair['anim'], {'x': {'frames': 3, 'w': 8, 'h': 6, 'ms': 100}})
        self.assertTrue(pair['x'].endswith('-strip.png'))
        with Image.open(self.root / 'out' / pair['x']) as strip:
            self.assertEqual(strip.size, (24, 6))
            self.assertEqual(strip.getpixel((16, 0)), (80, 0, 0, 255))
        self.assertTrue(pair['y'].endswith('.gif'))  # one frame: copied as is


class PickExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.config = self.root / 'picks.toml'
        self.config.write_text('[[lane]]\nkey = "icons"\nname = "Icons"\nquestion = "Which?"\npairs = "icons/pairs.json"\n'
                               '\n[[lane]]\nkey = "anim"\nname = "Anim"\nquestion = "Which?"\npairs = "anim/pairs.json"\n'
                               'answers = "out/anim-answers.json"\n')

    def export(self, dump) -> dict[str, int]:
        path = self.root / 'dump.json'
        path.write_text(json.dumps(dump))
        return pick_export.export(self.config, path)

    def test_writes_each_lanes_answers_latest_pick_wins(self) -> None:
        pick = lambda lane, pair, choice, at: {'lane': lane, 'pair': pair, 'choice': choice, 'left': 'x', 'at': at}
        dump = {'documents': [
            {'id': 'icons__i2', 'data': pick('icons', 'i2', 'x', '2026-11-23T10:00:00Z')},
            {'id': 'icons__i1', 'data': pick('icons', 'i1', 'tie', '2026-11-23T09:00:00Z')},
            {'id': 'icons__i2', 'data': pick('icons', 'i2', 'y', '2026-11-23T11:00:00Z')},
            {'id': 'old__o1', 'data': pick('old', 'o1', 'x', '2026-11-23T11:00:00Z')},
        ], 'next': None}
        self.assertEqual(self.export(dump), {'icons': 2, 'anim': 0})
        self.assertEqual(json.loads((self.root / 'icons/answers.json').read_text()), {'i1': 'tie', 'i2': 'y'})
        self.assertEqual(json.loads((self.root / 'out/anim-answers.json').read_text()), {})

    def test_bad_choice_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, 'choice'):
            self.export([{'lane': 'icons', 'pair': 'i1', 'choice': 'left'}])


class FlawRankTests(unittest.TestCase):
    """art-eval's planted-flaw check: a metric passes a flaw type when it orders sizes on enough items."""

    def row(self, item: int, scores: tuple, metric: str = 'dreamsim', flaw: str = 'bite') -> dict:
        return dict(zip(('item', 'flaw', 'metric', *flaw_rank.SIZES), (str(item), flaw, metric, *scores)))

    def test_order_follows_the_metrics_worse_direction(self) -> None:
        self.assertTrue(flaw_rank.ordered(self.row(1, (0, 0.1, 0.2, 0.3))))
        self.assertFalse(flaw_rank.ordered(self.row(1, (0, 0.2, 0.1, 0.3))))
        self.assertFalse(flaw_rank.ordered(self.row(1, (0, 0.1, 0.1, 0.3))))  # a tie is not ordered
        self.assertTrue(flaw_rank.ordered(self.row(1, (1, 0.9, 0.8, 0.7)), lower_is_worse=True))
        self.assertFalse(flaw_rank.ordered(self.row(1, (1, 0.9, 0.8, 0.7))))

    def test_threshold_and_resolution(self) -> None:
        good = [self.row(i, (0, 0.002 + i / 1000, 0.05, 0.1)) for i in range(9)]
        bad = [self.row(9, (0, 0.06, 0.05, 0.1))]
        iou = [self.row(i, (1, 0.9, 0.8, 0.7), 'iou') for i in range(10)]
        results = {(r['metric'], r['flaw']): r for r in flaw_rank.evaluate(good + bad + iou, 0.9, frozenset({'iou'}))}
        self.assertEqual((results['dreamsim', 'bite']['ordered'], results['dreamsim', 'bite']['passed']), (9, True))
        self.assertEqual(results['dreamsim', 'bite']['missed'], ['9'])
        self.assertTrue(results['iou', 'bite']['passed'])
        strict = flaw_rank.evaluate(good + bad, 0.95)
        self.assertFalse(strict[0]['passed'])
        res = flaw_rank.resolution(flaw_rank.evaluate(good + bad + iou, 0.9, frozenset({'iou'})))
        self.assertAlmostEqual(res['dreamsim'], 0.002)
        self.assertAlmostEqual(res['iou'], 0.1)
        self.assertEqual(flaw_rank.resolution(strict), {})  # no passing flaw type, no resolution

    def test_command_line_reads_csv(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        rows = ['item,flaw,metric,clean,small,medium,large'] + [f'{i},wing,lpips,0,0.1,0.2,0.3' for i in range(10)]
        (root / 'scores.csv').write_text('\n'.join(rows) + '\n')
        proc = subprocess.run([sys.executable, str(ART_EVAL / 'flaws/rank.py'), str(root / 'scores.csv'), '--json'],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual([(r['metric'], r['flaw'], r['passed']) for r in out['results']], [('lpips', 'wing', True)])
        (root / 'scores.csv').write_text('item,flaw,metric,clean,small\n1,wing,lpips,0,0.1\n')
        proc = subprocess.run([sys.executable, str(ART_EVAL / 'flaws/rank.py'), str(root / 'scores.csv')],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('missing medium, large', proc.stderr)


if __name__ == '__main__':
    unittest.main()
