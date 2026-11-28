"""Tests for the starter's Python helpers that rule cases can't reach (they run outside check.py's gates).

Covers every starter: the iOS one's check record and simulator lock, the Rust one's tool and toolchain setup (and the
inherited settings it drops), new-feature command and CI workflow, the TypeScript one's tool setup (Node.js, pnpm and
where installed packages go), and the Android one's tool setup (JDK, Gradle, the SDK's pinned revisions) and emulator
lock. Also the skills' tools: art-eval's pick page builder, its answer export and its planted-flaw ranking.

Usage: python3 scripts/test_starter_scripts.py
"""
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import tomllib
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'starters/ios/template'
RUST_TEMPLATE = ROOT / 'starters/rust/template'
TS_TEMPLATE = ROOT / 'starters/typescript/template'
ANDROID_TEMPLATE = ROOT / 'starters/android/template'
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
TEST_INTEGRITY = ROOT / 'skills/test-integrity/scan.py'

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
        env = self.rust_env()
        toolchain = self.tools / 'rust/rustup/toolchains/1.99.0-aarch64-apple-darwin'
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

    def rust_env(self) -> dict:
        # A toolchain already in the tools folder, so nothing is downloaded.
        toolchain = self.tools / 'rust/rustup/toolchains/1.99.0-aarch64-apple-darwin'
        (toolchain / 'bin').mkdir(parents=True, exist_ok=True)
        (toolchain / 'bin/cargo-clippy').write_text('')
        script = ('import json, sys; sys.path.insert(0, sys.argv[1]); from tools import rust_env; '
                  'print(json.dumps(rust_env()))')
        result = subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts')], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_rust_env_drops_inherited_settings_that_change_the_checks(self) -> None:
        self.env.update({'RUSTFLAGS': '-A warnings', 'CARGO_ENCODED_RUSTFLAGS': '-Awarnings',
                         'CARGO_PROFILE_DEV_OVERFLOW_CHECKS': 'false', 'CARGO_BUILD_RUSTC_WRAPPER': '/bin/true',
                         'RUSTC_WRAPPER': '/bin/true', 'CLIPPY_CONF_DIR': '/tmp', 'CLIPPY_ARGS': '-Aclippy::all',
                         'CARGO_TARGET_AARCH64_APPLE_DARWIN_RUNNER': 'true', 'CARGO_TERM_COLOR': 'always'})
        env = self.rust_env()
        self.assertEqual(env['RUSTFLAGS'], '-D warnings')
        self.assertEqual(env['CLIPPY_CONF_DIR'], str(self.root))  # every crate gets the root clippy.toml
        for dropped in ('CARGO_ENCODED_RUSTFLAGS', 'CARGO_PROFILE_DEV_OVERFLOW_CHECKS', 'CARGO_BUILD_RUSTC_WRAPPER',
                        'RUSTC_WRAPPER', 'CLIPPY_ARGS', 'CARGO_TARGET_AARCH64_APPLE_DARWIN_RUNNER'):
            self.assertNotIn(dropped, env)
        self.assertEqual(env['CARGO_TERM_COLOR'], 'always')  # output settings stay

    def test_a_tool_pinned_per_host_uses_this_hosts_pin(self) -> None:
        archive = self.fake_archive()
        here = {('Darwin', 'arm64'): 'mac-arm64', ('Linux', 'x86_64'): 'linux-x64'}[(platform.system(), platform.machine())]
        other = 'linux-x64' if here == 'mac-arm64' else 'mac-arm64'
        sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        (self.root / 'tools.toml').write_text(
            f'[fake]\nversion = "1.0"\n\n[fake.{here}]\nurl = "{archive.as_uri()}"\nsha256 = "{sha}"\n'
            f'binary = "fake-1.0/fake"\n\n[fake.{other}]\nurl = "file:///nowhere.tar.gz"\nsha256 = "{"0" * 64}"\n'
            'binary = "elsewhere/fake"\n')
        result = self.run_tools('fake')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), self.tools / 'fake-1.0/fake-1.0/fake')
        (self.root / 'tools.toml').write_text(f'[fake]\nversion = "2.0"\n\n[fake.{other}]\nurl = "file:///x.tar.gz"\n'
                                              f'sha256 = "{"0" * 64}"\nbinary = "fake"\n')
        refused = self.run_tools('fake')
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn(f'tools.toml pins fake for {other}, not {here}.', refused.stderr)

    def test_handback_helper_and_hooks_match_the_ios_starter_but_its_gates(self) -> None:
        strip = lambda text: [line for line in text.splitlines() if not line.startswith('GATES = ')]
        self.assertEqual(strip((RUST_TEMPLATE / 'scripts/handback.py').read_text()),
                         strip((TEMPLATE / 'scripts/handback.py').read_text()))
        gates = next(l for l in (RUST_TEMPLATE / 'scripts/handback.py').read_text().splitlines() if l.startswith('GATES = '))
        self.assertIn(gates.split(' = ', 1)[1], (RUST_TEMPLATE / 'scripts/check.py').read_text())
        for hook in ('.githooks/commit-msg', '.claude/settings.json'):
            self.assertEqual((RUST_TEMPLATE / hook).read_text(), (TEMPLATE / hook).read_text(), hook)
        self.assertTrue(os.access(RUST_TEMPLATE / '.githooks/commit-msg', os.X_OK))

    def test_the_starter_pins_cargo_deny_for_every_host(self) -> None:
        pins = tomllib.loads((RUST_TEMPLATE / 'tools.toml').read_text())['cargo-deny']
        self.assertEqual(sorted(k for k in pins if isinstance(pins[k], dict)), ['linux-x64', 'mac-arm64'])

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
        self.env['ELECTRON_RUN_AS_NODE'] = '1'
        self.env['VITEST_MAX_WORKERS'] = '18'
        env = json.loads(self.node_env().stdout)
        self.assertNotIn('npm_config_registry', env)
        self.assertNotIn('pnpm_config_registry', env)
        self.assertNotIn('ELECTRON_RUN_AS_NODE', env)
        self.assertNotIn('VITEST_MAX_WORKERS', env)

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

    def assert_reaped(self, pid: int) -> None:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            proc = subprocess.run(['ps', '-p', str(pid), '-o', 'state='], capture_output=True, text=True)
            state = proc.stdout.strip()
            if proc.returncode != 0 or not state or state.startswith('Z'):
                return
            time.sleep(0.02)
        self.fail(f'pid {pid} is still alive')

    def test_run_group_fails_and_reaps_detached_sip_binary_and_inherited_pipes_without_hanging(self) -> None:
        sip_grp = self.root / 'sip-grp.pid'
        sip_sid = self.root / 'sip-sid.pid'
        # 1. `/bin/sleep` in leader group with stdout/stderr inherited (Sol S3).
        # 2. Detached `setsid()` `/bin/sleep` (macOS SIP binary whose env `ps -E` hides, with exited parent: Sol S8).
        detached_sip = shlex.join([sys.executable, '-c',
                                   'import os, pathlib, subprocess\n'
                                   'p = subprocess.Popen(["/bin/sleep", "60"], start_new_session=True)\n'
                                   f'pathlib.Path({str(sip_sid)!r}).write_text(str(p.pid))\n'])
        cmd = ['sh', '-c',
               f'/bin/sleep 60 & printf "%s" "$!" > {shlex.quote(str(sip_grp))}; {detached_sip}; '
               f'while [ ! -s {shlex.quote(str(sip_grp))} ] || [ ! -s {shlex.quote(str(sip_sid))} ]; do sleep 0.02; done; '
               'echo done']
        script = ('import json, pathlib, sys; sys.path.insert(0, sys.argv[1]); from tools import run_group\n'
                  'proc = run_group(json.loads(sys.argv[2]), pathlib.Path(sys.argv[3]), {})\n'
                  'print(json.dumps([proc.returncode, proc.stdout.strip(), proc.stderr]))\n')
        result = subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts'), json.dumps(cmd), str(self.root)],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        returncode, stdout, stderr = json.loads(result.stdout)
        self.assertEqual(returncode, 1)
        self.assertEqual(stdout, 'done')
        self.assertIn('[no-concurrency-escapes]', stderr)
        for pid_file in (sip_grp, sip_sid):
            self.assert_reaped(int(pid_file.read_text()))

    def test_compiler_pool_cancellation_aborts_active_and_starting_workers(self) -> None:
        # Sol S9 + S16 + S17: lock-free signal handler + sticky abort stops both running and paused-before-register workers.
        worker_pid = self.root / 'compiler-worker.pid'
        late_ran = self.root / 'late-worker.ran'
        runner = (
            'import os, pathlib, sys, threading, time\n'
            'from concurrent.futures import ThreadPoolExecutor\n'
            'sys.path.insert(0, sys.argv[1])\n'
            'from tools import abort_active, handle_termination, reset_abort, run_group\n'
            'handle_termination()\n'
            'reset_abort()\n'
            'cmd = ["sh", "-c", f"/bin/sleep 60 & echo $! > {sys.argv[2]}; wait"]\n'
            'late_cmd = ["sh", "-c", f"echo ran > {sys.argv[4]}"]\n'
            'entered = threading.Event()\n'
            'def late():\n'
            '    entered.set()\n'
            '    time.sleep(0.3)\n'
            '    return run_group(late_cmd, pathlib.Path(sys.argv[3]), dict(os.environ))\n'
            'pool = ThreadPoolExecutor(max_workers=2)\n'
            'futures = []\n'
            'try:\n'
            '    futures.append(pool.submit(run_group, cmd, pathlib.Path(sys.argv[3]), dict(os.environ)))\n'
            '    futures.append(pool.submit(late))\n'
            '    entered.wait(timeout=5)\n'
            '    [f.result() for f in futures]\n'
            'except BaseException:\n'
            '    from tools import defer_signals\n'
            '    with defer_signals(reraise=False, clear_pending=True):\n'
            '        abort_active()\n'
            '        for f in futures: f.cancel()\n'
            '        pool.shutdown(wait=True, cancel_futures=True)\n'
            '    sys.exit(130)\n'
        )
        proc = subprocess.Popen([sys.executable, '-c', runner, str(self.root / 'scripts'),
                                 str(worker_pid), str(self.root), str(late_ran)],
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while not worker_pid.is_file() or not worker_pid.read_text().strip():
                self.assertLess(time.monotonic(), deadline, 'compiler worker never started')
                time.sleep(0.02)
            pid = int(worker_pid.read_text())
            proc.send_signal(signal.SIGTERM)
            proc.communicate(timeout=10)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
        self.assert_reaped(pid)
        self.assertFalse(late_ran.exists(), 'starting worker ran after abort_active()')

    def test_run_group_kills_nested_and_setsid_trees_on_sigint_and_sigterm(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig.name):
                inner_file = self.root / f'inner-{sig.name}.pid'
                sid_file = self.root / f'sid-{sig.name}.pid'
                sid_child = shlex.join([sys.executable, '-c',
                                        'import os, pathlib, signal, time\n'
                                        'if os.fork() > 0: os._exit(0)\n'
                                        'os.setsid()\n'
                                        'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                                        f'pathlib.Path({str(sid_file)!r}).write_text(str(os.getpid()))\n'
                                        'time.sleep(60)\n'])
                inner_cmd = ['sh', '-c',
                             f'{sid_child}; '
                             'python3 -c \'import os, pathlib, signal, sys, time; '
                             'signal.signal(signal.SIGTERM, signal.SIG_IGN); '
                             'pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)\' '
                             f'{shlex.quote(str(inner_file))}']
                inner_runner = shlex.join([sys.executable, '-c',
                                           'import json, os, pathlib, sys; sys.path.insert(0, sys.argv[1]); '
                                           'from reap import handle_termination, run_group; handle_termination(); '
                                           'run_group(json.loads(sys.argv[2]), pathlib.Path(sys.argv[3]), dict(os.environ))',
                                           str(self.root / 'scripts'), json.dumps(inner_cmd), str(self.root)])
                outer_runner = ('import os, pathlib, sys; sys.path.insert(0, sys.argv[1]); '
                                'from reap import handle_termination, run_group; handle_termination()\n'
                                'try:\n'
                                '    run_group(["sh", "-c", sys.argv[2]], pathlib.Path(sys.argv[3]), dict(os.environ))\n'
                                'except KeyboardInterrupt:\n'
                                '    sys.exit(130)\n')
                proc = subprocess.Popen([sys.executable, '-c', outer_runner, str(self.root / 'scripts'),
                                         inner_runner, str(self.root)],
                                        env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    deadline = time.monotonic() + 10
                    while not (inner_file.is_file() and inner_file.read_text().strip()
                               and sid_file.is_file() and sid_file.read_text().strip()):
                        self.assertLess(time.monotonic(), deadline, 'nested children never wrote their pids')
                        time.sleep(0.02)
                    pids = [int(inner_file.read_text()), int(sid_file.read_text())]
                    proc.send_signal(sig)
                    proc.communicate(timeout=10)
                finally:
                    if proc.poll() is None:
                        proc.kill()
                        proc.communicate()
                for pid in pids:
                    self.assert_reaped(pid)

    def test_verify_workers_reads_env_and_machine_config_without_hardcoding(self) -> None:
        home = self.root / 'home'
        cfg = home / '.config/b-stack'
        cfg.mkdir(parents=True)
        (cfg / 'config.toml').write_text(f'cache_dir = "{self.cache}"\nverify_workers = 3\n')
        probe = ('import os, sys; sys.path.insert(0, sys.argv[1]); import verify; '
                 'print(verify.verify_workers(dict(os.environ)))')
        base_env = {k: v for k, v in self.env.items() if k != 'BSTACK_VERIFY_WORKERS'} | {'HOME': str(home)}
        from_cfg = subprocess.run([sys.executable, '-c', probe, str(self.root / 'scripts')],
                                  env=base_env, capture_output=True, text=True)
        self.assertEqual((from_cfg.returncode, from_cfg.stdout.strip()), (0, '3'), from_cfg.stderr)
        from_env = subprocess.run([sys.executable, '-c', probe, str(self.root / 'scripts')],
                                  env={**base_env, 'BSTACK_VERIFY_WORKERS': '2'}, capture_output=True, text=True)
        self.assertEqual((from_env.returncode, from_env.stdout.strip()), (0, '2'), from_env.stderr)

    def test_volume_loss_watchdog_kills_tree_immediately(self) -> None:
        mount = self.root / 'simulated-mount'
        mount.mkdir()
        grp_pid = self.root / 'vol-grp.pid'
        sid_pid = self.root / 'vol-sid.pid'
        detached = shlex.join([sys.executable, '-c',
                               'import pathlib, signal, subprocess\n'
                               'p = subprocess.Popen(["/bin/sleep", "60"], start_new_session=True)\n'
                               f'pathlib.Path({str(sid_pid)!r}).write_text(str(p.pid))\n'])
        cmd = ['sh', '-c', f'/bin/sleep 60 & echo $! > {shlex.quote(str(grp_pid))}; {detached}; wait']
        runner = ('import json, os, pathlib, sys; sys.path.insert(0, sys.argv[1]); from tools import run_group\n'
                  'proc = run_group(json.loads(sys.argv[2]), pathlib.Path(sys.argv[3]), dict(os.environ))\n'
                  'print(json.dumps([proc.returncode, proc.stderr]))\n')
        proc = subprocess.Popen([sys.executable, '-c', runner, str(self.root / 'scripts'), json.dumps(cmd), str(self.root)],
                                env={**self.env, 'BSTACK_WATCH_PATH': str(mount)},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while not (grp_pid.is_file() and grp_pid.read_text().strip()
                       and sid_pid.is_file() and sid_pid.read_text().strip()):
                self.assertLess(time.monotonic(), deadline, 'children never started')
                time.sleep(0.02)
            pids = [int(grp_pid.read_text()), int(sid_pid.read_text())]
            shutil.rmtree(mount)
            stdout, stderr = proc.communicate(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
        self.assertEqual(proc.returncode, 0, stderr)
        returncode, err = json.loads(stdout)
        self.assertEqual(returncode, 1)
        self.assertIn('[volume-lost]', err)
        for pid in pids:
            self.assert_reaped(pid)

    def test_volume_watchdog_uses_effective_cache_and_rejects_missing_watch_path_before_spawn(self) -> None:
        # Sol S22 + S25: BSTACK_CACHE_DIR overrides an unmounted config.toml cache_dir, and a missing required path
        # fails before the command ever runs.
        home = self.root / 'home-vol'
        cfg = home / '.config/b-stack'
        cfg.mkdir(parents=True)
        (cfg / 'config.toml').write_text(f'cache_dir = "{self.root / "unmounted-toml"}"\n')
        marker = self.root / 'never-ran.txt'
        script = (
            'import json, os, pathlib, sys; sys.path.insert(0, sys.argv[1]); from tools import reset_abort, run_group\n'
            'ok = run_group(["sh", "-c", "echo ok"], pathlib.Path(sys.argv[2]), dict(os.environ))\n'
            'bad = run_group(["sh", "-c", f"echo oops > {sys.argv[3]}"], pathlib.Path(sys.argv[2]), '
            '{**os.environ, "BSTACK_WATCH_PATH": sys.argv[4]})\n'
            'bad_tools = run_group(["sh", "-c", f"echo oops > {sys.argv[3]}"], pathlib.Path(sys.argv[2]), '
            '{**os.environ, "BSTACK_TOOLS_DIR": sys.argv[5]})\n'
            'print(json.dumps([ok.returncode, ok.stdout.strip(), bad.returncode, bad.stderr, bad_tools.returncode, bad_tools.stderr]))\n'
        )
        res = subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts'), str(self.root),
                              str(marker), str(self.root / 'missing-mount'), str(self.root / 'absent-vol/tools')],
                             env={**self.env, 'HOME': str(home)}, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, res.stderr)
        ok_rc, ok_out, bad_rc, bad_err, tools_rc, tools_err = json.loads(res.stdout)
        self.assertEqual((ok_rc, ok_out), (0, 'ok'))
        self.assertEqual(bad_rc, 1)
        self.assertIn('[volume-lost]', bad_err)
        self.assertEqual(tools_rc, 1)
        self.assertIn('[volume-lost]', tools_err)
        self.assertFalse(marker.exists())


class AndroidToolsTests(unittest.TestCase):
    """The Android starter's scripts/tools.py and emulator lock, in a copy of its scripts with fake tool archives."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ANDROID_TEMPLATE / 'scripts', self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        self.tools = self.root / 'tools'
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        self.env = {**os.environ, 'BSTACK_TOOLS_DIR': str(self.tools), 'BSTACK_CACHE_DIR': str(self.cache),
                    'GRADLE_USER_HOME': '/home/gradle', 'ANDROID_HOME': '/home/sdk'}

    def archive(self, name: str, script: str, zipped: bool = False) -> tuple[Path, str]:
        source = self.root / f'src/{name}/bin'
        source.mkdir(parents=True)
        (source / name).write_text(script)
        (source / name).chmod(0o755)
        if zipped:
            archive = self.root / f'{name}.zip'
            subprocess.run(['ditto', '-c', '-k', str(self.root / f'src/{name}'), str(archive)], check=True)
        else:
            archive = self.root / f'{name}.tar.gz'
            subprocess.run(['tar', 'czf', str(archive), '-C', str(self.root / 'src'), name], check=True)
        return archive, hashlib.sha256(archive.read_bytes()).hexdigest()

    def pin(self, jdk_sha: str | None = None, installs: str = '2') -> None:
        """A fake JDK (tar.gz) and command-line tools (zip) whose sdkmanager installs revision `installs`."""
        jdk, jdk_digest = self.archive('jdk', '#!/bin/sh\necho jdk\n')
        sdkmanager = ('#!/bin/sh\nfor a in "$@"; do case "$a" in --sdk_root=*) root="${a#--sdk_root=}";; esac; done\n'
                      f'mkdir -p "$root/platforms/android-1" && echo "Pkg.Revision={installs}" > "$root/platforms/android-1/source.properties"\n')
        tools_zip, tools_digest = self.archive('sdkmanager', sdkmanager, zipped=True)
        (self.root / 'tools.toml').write_text(
            f'[jdk]\nversion = "1.0"\nurl = "{jdk.as_uri()}"\nsha256 = "{jdk_sha or jdk_digest}"\nhome = "jdk"\n'
            f'[cmdline-tools]\nversion = "1.0"\nurl = "{tools_zip.as_uri()}"\nsha256 = "{tools_digest}"\nhome = "."\n'
            '[android-sdk.packages]\n"platforms;android-1" = "2"\n')

    def call(self, expression: str) -> subprocess.CompletedProcess:
        script = f'import json, sys; sys.path.insert(0, sys.argv[1]); import tools; print(json.dumps({expression}))'
        return subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts')], env=self.env,
                              capture_output=True, text=True)

    def test_tool_env_keeps_the_jdk_sdk_and_gradle_in_the_tools_folder(self) -> None:
        self.pin()
        result = self.call('tools.tool_env()')
        self.assertEqual(result.returncode, 0, result.stderr)
        env = json.loads(result.stdout)
        self.assertEqual(env['JAVA_HOME'], str(self.tools / 'jdk-1.0/jdk'))
        self.assertEqual(env['ANDROID_HOME'], str(self.tools / 'android-sdk'))
        self.assertEqual(env['GRADLE_USER_HOME'], str(self.tools / 'gradle-home'))
        self.assertEqual(env['ANDROID_AVD_HOME'], str(self.tools / 'android-user/avd'))
        self.assertEqual(env['PATH'].split(os.pathsep)[0], str(self.tools / 'jdk-1.0/jdk/bin'))

    def test_gradle_keeps_its_project_cache_at_the_build_folders_real_path(self) -> None:
        # Through the .build link, Gradle 9.9.2 deletes every output as stale and reruns every task. The link is made
        # first, so this holds before anything else has made it.
        result = self.call('(setattr(tools, "tool_path", lambda name: tools.Path("/gradle")), tools.gradle_command("x"))[1]')
        self.assertEqual(result.returncode, 0, result.stderr)
        command = json.loads(result.stdout)
        self.assertTrue((self.root / '.build').is_symlink())
        real = (self.root / '.build').resolve()
        self.assertTrue(real.is_relative_to(self.cache))
        self.assertEqual(command[command.index('--project-cache-dir') + 1], str(real / 'gradle-project'))
        self.assertIn(f'-Pkotlin.project.persistent.dir={real / "kotlin"}', command)

    def test_rule_runs_turn_off_kotlins_incremental_compiler_with_a_plain_variable(self) -> None:
        expression = '(setattr(tools, "tool_path", lambda name: tools.Path("/gradle")), tools.gradle_command("x"))[1]'
        self.env.pop('BSTACK_KOTLIN_INCREMENTAL', None)
        self.assertNotIn('-Pkotlin.incremental=false', json.loads(self.call(expression).stdout))
        self.env['BSTACK_KOTLIN_INCREMENTAL'] = 'false'
        command = json.loads(self.call(expression).stdout)
        self.assertLessEqual({'-Pkotlin.incremental=false', '-Pkotlin.incremental.multiplatform=false'}, set(command))

    def test_sdk_installs_the_pinned_revision(self) -> None:
        self.pin()
        result = self.call('str(tools.sdk())')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.tools / 'android-sdk/platforms/android-1/source.properties').is_file())

    def test_a_newer_sdk_revision_than_pinned_stops(self) -> None:
        self.pin(installs='3')
        result = self.call('str(tools.sdk())')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('platforms;android-1 3 (pinned 2)', result.stderr)

    def test_checksum_mismatch_is_refused_and_leaves_nothing(self) -> None:
        self.pin(jdk_sha='0' * 64)
        result = self.call('str(tools.tool_path("jdk"))')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stderr)
        self.assertFalse((self.tools / 'jdk-1.0').exists())

    def test_missing_cache_drive_stops_instead_of_building_elsewhere(self) -> None:
        self.pin()
        del self.env['BSTACK_TOOLS_DIR']
        self.env['BSTACK_CACHE_DIR'] = str(self.root / 'unmounted')
        result = self.call('str(tools.tool_path("jdk"))')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Is its drive mounted?', result.stderr)

    def test_paths_helper_matches_the_ios_starter(self) -> None:
        self.assertEqual((ANDROID_TEMPLATE / 'scripts/paths.py').read_text(), (TEMPLATE / 'scripts/paths.py').read_text())

    def test_handback_helper_matches_the_ios_starter_but_its_gates(self) -> None:
        strip = lambda text: [line for line in text.splitlines() if not line.startswith('GATES = ')]
        self.assertEqual(strip((ANDROID_TEMPLATE / 'scripts/handback.py').read_text()),
                         strip((TEMPLATE / 'scripts/handback.py').read_text()))
        gates = next(l for l in (ANDROID_TEMPLATE / 'scripts/handback.py').read_text().splitlines() if l.startswith('GATES = '))
        self.assertIn(gates.split(' = ', 1)[1], (ANDROID_TEMPLATE / 'scripts/check.py').read_text())

    def test_second_emulator_holder_waits_and_says_who_holds_it(self) -> None:
        home = self.root / 'home'
        holder = ('import sys, time; sys.path.insert(0, sys.argv[1]); import emulator\n'
                  'with emulator.in_use("first holder"):\n    print("held", flush=True); time.sleep(2)\n')
        env = {**self.env, 'HOME': str(home)}
        env.pop('BSTACK_EMULATOR_LOCK', None)
        first = subprocess.Popen([sys.executable, '-c', holder, str(self.root / 'scripts')], env=env,
                                 stdout=subprocess.PIPE, text=True)
        self.assertEqual(first.stdout.readline().strip(), 'held')
        second = subprocess.run([sys.executable, '-c', holder, str(self.root / 'scripts')], env=env, capture_output=True,
                                text=True, timeout=30)
        first.wait()
        first.stdout.close()
        self.assertIn('waiting for the emulator: in use by pid', second.stdout)
        self.assertIn('first holder', second.stdout)
        self.assertIn('held', second.stdout)


def code_owned(template: Path, path: str) -> bool:
    """Whether the template's CODEOWNERS owns `path` (relative to the project). Every rule there is anchored (/...) and
    names an owner (the settings gate requires one), so any matching rule owns it."""
    patterns = [re.sub(r'(^|\s)#.*$', '', line).split() for line in (template / 'CODEOWNERS').read_text().splitlines()]
    return any(p[0].endswith('/') and f'/{path}'.startswith(p[0]) or f'/{path}' == p[0] for p in patterns if len(p) > 1)


def files_in(root: Path) -> dict[str, bytes]:
    return {str(f.relative_to(root)): f.read_bytes() for f in root.rglob('*')
            if f.is_file() and f.relative_to(root).parts[0] != 'scripts'}


def written(root: Path, run: callable) -> list[str]:
    """The files under `root` (outside scripts/) that `run` added or changed."""
    before = files_in(root)
    run()
    return sorted(path for path, data in files_in(root).items() if before.get(path) != data)


class AndroidCheckTests(unittest.TestCase):
    """check.py's Gradle gates: one Gradle run for all of them when it passes, each on its own when it doesn't."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ANDROID_TEMPLATE / 'scripts', self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ANDROID_TEMPLATE / 'arch', self.root / 'arch', ignore=shutil.ignore_patterns('detekt-rules', 'konsist'))

    def run_check(self, failing: set[str], gates: list[str], skipped: bool = False) -> tuple[list[list[str]], list[str], str]:
        """check.check(gates) with a fake Gradle that fails any run including a task in `failing`, and leaves passing
        results for Konsist and module `m` (skipped ones with `skipped`): (each Gradle run's tasks, the failed gates,
        the output)."""
        script = textwrap.dedent('''
            import contextlib, io, json, sys
            sys.path.insert(0, sys.argv[1])
            import check
            runs, failing, skipped = [], set(json.loads(sys.argv[2])), sys.argv[4] == 'skipped'
            def result(folder, status):
                path = check.RESULTS / folder / 'test-results/test/TEST-t.xml'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f'<testsuite><testcase classname="T" name="t">{status}</testcase></testsuite>')
            def gradle(env, *tasks):
                runs.append(list(tasks))
                if ':arch:konsist:test' in tasks:
                    result('arch/konsist', '')
                if 'jvmTest' in tasks:
                    result('m', '<skipped/>' if skipped else '')
                return not failing & set(tasks), 'gradle output'
            check.gradle, check.android_env = gradle, dict
            check.tested_modules = lambda: ['m']
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                failed = check.check(json.loads(sys.argv[3]))
            print(json.dumps([runs, failed, out.getvalue()]))
        ''')
        result = subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts'), json.dumps(sorted(failing)),
                                 json.dumps(gates), 'skipped' if skipped else ''], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.splitlines()[-1])

    def test_passing_gates_share_one_gradle_run_but_lint_runs_alone(self) -> None:
        runs, failed, output = self.run_check(set(), ['compiler', 'detekt', 'lint'])
        self.assertEqual(failed, [])
        self.assertEqual(len(runs), 2)
        self.assertLessEqual({'assembleDebug', 'detektMainJvm'}, set(runs[0]))
        self.assertNotIn('lintDebug', runs[0])
        self.assertEqual(runs[1], ['lintDebug'])
        self.assertIn('One Gradle run for compiler, detekt: passed', output)

    def test_a_failing_shared_run_reruns_each_gate_so_the_failure_is_its_own(self) -> None:
        runs, failed, output = self.run_check({'detektMain'}, ['compiler', 'detekt', 'lint'])
        self.assertEqual(failed, ['detekt'])
        self.assertEqual(runs[1:], [list(tasks) for tasks in (
            ('assembleDebug', 'compileCommonMainKotlinMetadata', 'compileTestKotlinJvm', 'compileDebugUnitTestKotlin',
             'testClasses'), ('detektMainJvm', 'detektTestJvm', 'detektMain', 'detektTest'), ('lintDebug',))])
        self.assertIn('PASS compiler', output)
        self.assertIn('FAIL detekt', output)
        self.assertIn('PASS lint', output)

    def test_a_passing_shared_run_still_fails_a_skipped_test(self) -> None:
        runs, failed, output = self.run_check(set(), ['compiler', 'konsist', 'tests'], skipped=True)
        self.assertEqual((len(runs), failed), (1, ['tests']))
        self.assertIn('[tests-always-run] m: T.t was skipped', output)

    def test_konsist_without_results_fails(self) -> None:
        script = ('import sys; sys.path.insert(0, sys.argv[1]); import check\n'
                  'print(check.judge("konsist", True, ""))')
        result = subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts')], capture_output=True, text=True)
        self.assertIn("(False,", result.stdout, result.stderr)
        self.assertIn("didn't run", result.stdout)

    def test_one_gate_runs_alone(self) -> None:
        runs, failed, _ = self.run_check(set(), ['konsist'])
        self.assertEqual((runs, failed), ([[':arch:konsist:test']], []))


class AndroidDepsTests(unittest.TestCase):
    """deps.py's manifest + shipped libraries: one Gradle run when both pass, separate runs on failure."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ANDROID_TEMPLATE / 'scripts', self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ANDROID_TEMPLATE / 'arch', self.root / 'arch', ignore=shutil.ignore_patterns('detekt-rules', 'konsist'))

    def run_deps(self, combined_rc: int) -> tuple[list[list[str]], list[str], list[str]]:
        script = textwrap.dedent('''
            import json, subprocess, sys
            sys.path.insert(0, sys.argv[1])
            import deps
            runs, combined_rc = [], int(sys.argv[2])
            def fake_cmd(*args):
                return ['gradle', *args]
            def fake_run(cmd, **kwargs):
                runs.append(cmd[1:])
                if ':app:processReleaseMainManifest' in cmd:
                    deps.MERGED.parent.mkdir(parents=True, exist_ok=True)
                    deps.MERGED.write_text('<manifest package="dev.bstack.starter"><application/></manifest>')
                rc = combined_rc if len(runs) == 1 else 0
                out = '+--- com.example:lib:1.0\\n' if ':app:dependencies' in cmd else ''
                return subprocess.CompletedProcess(cmd, rc, out, '')
            deps.gradle_command = fake_cmd
            deps.subprocess.run = fake_run
            findings, in_app = deps.manifest_and_shipped({})
            print(json.dumps([runs, findings, sorted(in_app)]))
        ''')
        result = subprocess.run([sys.executable, '-c', script, str(self.root / 'scripts'), str(combined_rc)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.splitlines()[-1])

    def test_combined_run_avoids_second_gradle_call(self) -> None:
        runs, findings, in_app = self.run_deps(0)
        self.assertEqual(len(runs), 1)
        self.assertEqual((findings, in_app), ([], ['com.example:lib']))

    def test_failed_combined_run_falls_back_to_separate_runs(self) -> None:
        runs, findings, in_app = self.run_deps(1)
        self.assertEqual(len(runs), 3)
        self.assertEqual((findings, in_app), ([], ['com.example:lib']))


class RuleWorkersTests(unittest.TestCase):
    """test_rules.py's default workers for Android, from the machine's cores and memory (platforms.gradle_workers)."""

    def workers(self, cores: int, memory_gb: int) -> int:
        sys.path.insert(0, str(ROOT / 'scripts'))
        import platforms
        pages = {'SC_PAGE_SIZE': 4096, 'SC_PHYS_PAGES': memory_gb * 2**30 // 4096}
        with mock.patch.object(platforms.os, 'cpu_count', return_value=cores), \
                mock.patch.object(platforms.os, 'sysconf', side_effect=pages.__getitem__):
            return platforms.gradle_workers()

    def test_ci_runner_gets_one_and_this_mac_mini_four(self) -> None:
        self.assertEqual(self.workers(2, 8), 1)
        self.assertEqual(self.workers(4, 16), 1)
        self.assertEqual(self.workers(10, 16), 2)
        self.assertEqual(self.workers(12, 24), 4)
        self.assertEqual(self.workers(24, 64), 4)


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

    def test_nothing_a_feature_adds_is_code_owned(self) -> None:
        # A feature's pull request waits for the owner only if it touches enforcement: not for what new_feature.py
        # writes, the composition roots that show it, its fixtures or the lockfile entry its package adds.
        made = written(self.root, lambda: self.assertEqual(self.run_new('notes').returncode, 0))
        self.assertIn('feature-map/notes.toml', made)
        for path in made + ['apps/desktop/src/main.ts', 'apps/web/src/main.tsx', 'packages/fixtures/src/index.ts',
                            'pnpm-lock.yaml']:
            self.assertFalse(code_owned(TS_TEMPLATE, path), path)
        for path in ('apps/desktop/journeys/support/app.ts', 'apps/desktop/journeys/tsconfig.json', 'arch/retired.toml',
                     'arch/shape.json', 'scripts/verify.py', '.github/workflows/check.yml', 'package.json'):
            self.assertTrue(code_owned(TS_TEMPLATE, path), path)

    def test_refuses_a_bad_name_and_an_existing_feature(self) -> None:
        self.assertEqual(self.run_new('Notes').returncode, 2)
        self.assertEqual(self.run_new('two words').returncode, 2)
        self.assertEqual(self.run_new('notes').returncode, 0)
        again = self.run_new('notes')
        self.assertEqual(again.returncode, 1)
        self.assertIn('already exist', again.stderr)

    def test_in_existing_package_adds_map_entry_journey_and_test_only(self) -> None:
        self.assertEqual(self.run_new('battle').returncode, 0)
        missing = self.run_new('undo-move', '--in', 'missing')
        self.assertEqual(missing.returncode, 1)
        self.assertIn("packages/features/missing isn't a feature package", missing.stderr)
        made = written(self.root, lambda: self.assertEqual(self.run_new('undo-move', '--in', 'battle').returncode, 0))
        self.assertEqual(made, [
            'apps/desktop/journeys/undo-move.journey.ts',
            'feature-map/undo-move.toml',
            'packages/features/battle/tests/undo-move.test.ts',
        ])
        for path in made:
            self.assertFalse(code_owned(TS_TEMPLATE, path), path)
        entry = tomllib.loads((self.root / 'feature-map/undo-move.toml').read_text())
        self.assertEqual((entry['id'], entry['modules'], entry['journeys'][0]['name']),
                         ('undo-move', ['battle'], 'undo_move_works'))
        self.assertFalse((self.root / 'packages/features/undo-move').exists())
        again = self.run_new('undo-move', '--in', 'battle')
        self.assertEqual(again.returncode, 1)
        self.assertIn('already exist', again.stderr)


class AndroidNewFeatureTests(unittest.TestCase):
    """The Android starter's scripts/new_feature.py, in a copy of its scripts, the modules it links and the runner.
    (That a created feature passes the gates, and its test and journey fail until written, was checked on the starter.)"""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ANDROID_TEMPLATE / 'scripts', self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        for module in ('app', 'app-verify', 'verify/journeys'):
            (self.root / module).mkdir(parents=True)
            shutil.copy2(ANDROID_TEMPLATE / module / 'module.toml', self.root / module / 'module.toml')
        shutil.copytree(ANDROID_TEMPLATE / 'verify/journeys/src', self.root / 'verify/journeys/src')
        shutil.copytree(ANDROID_TEMPLATE / 'verify/runner/src', self.root / 'verify/runner/src')

    def run_new(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / 'scripts/new_feature.py'), *args], capture_output=True,
                              text=True)

    def test_creates_the_modules_map_entry_journey_links_and_adapters(self) -> None:
        result = self.run_new('notes')
        self.assertEqual(result.returncode, 0, result.stderr)
        feature = self.root / 'features/notes'
        self.assertEqual(sorted(p.name for p in feature.iterdir()), ['api', 'logic', 'ui'])
        self.assertIn('val title = UiId("notes.title")', (feature / 'api/src/commonMain/kotlin/notes/api/NotesUi.kt').read_text())
        self.assertIn('fail("Write this test', (feature / 'logic/src/commonTest/kotlin/notes/logic/NotesModelTest.kt').read_text())
        self.assertIn('fun NotesRoute(model: NotesModel)', (feature / 'ui/src/main/kotlin/notes/ui/NotesScreen.kt').read_text())
        self.assertIn('modules = ["notes"]', (self.root / 'feature-map/notes.toml').read_text())
        journey = (self.root / 'verify/journeys/src/commonMain/kotlin/journeys/NotesJourneys.kt').read_text()
        for step in ('fun Journey.notesWorks()', 'screen.rotate()', 'screen.returnAfterProcessDeath()', '"Write this journey'):
            self.assertIn(step, journey)
        self.assertIn('fun notesWorks() = Driver("notesWorks").notesWorks()',
                      (self.root / 'verify/runner/src/main/kotlin/runner/Journeys.kt').read_text())
        self.assertIn('"features/notes/api"]', (self.root / 'verify/journeys/module.toml').read_text())
        for app in ('app', 'app-verify'):
            self.assertIn('"features/notes/api", "features/notes/logic", "features/notes/ui"]',
                          (self.root / app / 'module.toml').read_text())

    def test_nothing_a_feature_adds_is_code_owned(self) -> None:
        # What new_feature.py writes (modules, map entry, journey, regenerated adapters, links), the composition roots
        # that show the feature and its fixtures are the feature's; the journey kit and driver stay the owner's.
        made = written(self.root, lambda: self.assertEqual(self.run_new('notes').returncode, 0))
        self.assertIn('verify/runner/src/main/kotlin/runner/Journeys.kt', made)
        for path in made + ['app/src/main/kotlin/app/MainActivity.kt', 'app-verify/src/main/AndroidManifest.xml',
                            'fixtures/src/main/kotlin/fixtures/Fixtures.kt']:
            self.assertFalse(code_owned(ANDROID_TEMPLATE, path), path)
        for path in ('verify/runner/src/main/kotlin/runner/Driver.kt', 'verify/journeykit/module.toml', 'core-ui/x.kt',
                     'core/src/commonMain/kotlin/core/UiId.kt', 'arch/retired.toml', 'build-logic/x', 'scripts/verify.py',
                     '.github/workflows/check.yml', 'gradle/libs.versions.toml'):
            self.assertTrue(code_owned(ANDROID_TEMPLATE, path), path)

    def test_refuses_a_bad_name_and_an_existing_feature(self) -> None:
        for bad in ('Notes', 'daily-notes', 'two words', 'object', '1notes'):
            self.assertEqual(self.run_new(bad).returncode, 2, bad)
        self.assertEqual(self.run_new('notes').returncode, 0)
        again = self.run_new('notes')
        self.assertEqual(again.returncode, 1)
        self.assertIn('already exist', again.stderr)


class AndroidFeatureInModuleTests(unittest.TestCase):
    """`new_feature.py <id> --in <module>`: a feature whose code goes in a module another feature has."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for folder in ('scripts', 'features', 'feature-map', 'verify/journeys/src', 'verify/runner/src'):
            shutil.copytree(ANDROID_TEMPLATE / folder, self.root / folder, ignore=shutil.ignore_patterns('__pycache__'))

    def run_new(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / 'scripts/new_feature.py'), *args], capture_output=True,
                              text=True)

    def test_adds_a_map_entry_naming_the_module_a_journey_stub_and_a_test_stub(self) -> None:
        made = written(self.root, lambda: self.assertEqual(self.run_new('undo-move', '--in', 'tally').returncode, 0))
        self.assertEqual(made, ['feature-map/undo-move.toml',
                                'features/tally/logic/src/commonTest/kotlin/tally/logic/UndoMoveTest.kt',
                                'verify/journeys/src/commonMain/kotlin/journeys/UndoMoveJourneys.kt',
                                'verify/runner/src/main/kotlin/runner/Journeys.kt'])
        entry = tomllib.loads((self.root / 'feature-map/undo-move.toml').read_text())
        self.assertEqual((entry['modules'], entry['journeys'][0]['name']), (['tally'], 'undoMoveWorks'))
        journey = (self.root / 'verify/journeys/src/commonMain/kotlin/journeys/UndoMoveJourneys.kt').read_text()
        for step in ('fun Journey.undoMoveWorks()', 'screen.rotate()', 'screen.returnAfterProcessDeath()',
                     'screen.find(TallyUi.name).shows(', '"Write this journey'):
            self.assertIn(step, journey)
        self.assertIn('fail("Write this test',
                      (self.root / 'features/tally/logic/src/commonTest/kotlin/tally/logic/UndoMoveTest.kt').read_text())
        for path in made:
            self.assertFalse(code_owned(ANDROID_TEMPLATE, path), path)
        check = subprocess.run([sys.executable, str(self.root / 'scripts/verify.py'), 'map'], cwd=self.root,
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 1)
        self.assertIn('[verified-features] journey `undoMoveWorks` is still the stub new_feature.py wrote.', check.stdout)
        self.assertNotIn('modules', check.stdout)  # sharing tally's module is fine

    def test_finds_the_modules_ids_however_they_are_declared(self) -> None:
        ui = self.root / 'features/tally/api/src/commonMain/kotlin/tally/api/TallyUi.kt'
        ui.unlink()
        (ui.parent / 'Screens.kt').write_text('package tally.api.screens\n\nimport core.UiId\n\nobject ListUi {\n'
                                             '    public val rows: UiId = UiId("tally.rows")\n}\n')
        self.assertEqual(self.run_new('undo', '--in', 'tally').returncode, 0)
        journey = (self.root / 'verify/journeys/src/commonMain/kotlin/journeys/UndoJourneys.kt').read_text()
        self.assertIn('import tally.api.screens.ListUi\n', journey)
        self.assertIn('screen.find(ListUi.rows).shows(', journey)

    def test_refuses_a_missing_module_a_bad_id_and_an_existing_entry(self) -> None:
        missing = self.run_new('combat', '--in', 'battle')
        self.assertEqual(missing.returncode, 1)
        self.assertIn("features/battle isn't a feature module (there are: tally)", missing.stderr)
        for bad in ('Combat', 'two words', 'undo_move', '-undo'):
            self.assertEqual(self.run_new(bad, '--in', 'tally').returncode, 2, bad)
        self.assertEqual(self.run_new('tally', '--in', 'tally').returncode, 1)  # feature-map/tally.toml exists


class AndroidNewClientTests(unittest.TestCase):
    """`new_client.py <feature> <name>` in a copy of the starter's scripts, shape, tally feature, fixtures and both apps.
    (That what it creates passes every gate was checked on the starter and on Hexfleet.)"""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for folder in ('scripts', 'arch', 'features', 'fixtures', 'app', 'app-verify'):
            shutil.copytree(ANDROID_TEMPLATE / folder, self.root / folder,
                            ignore=shutil.ignore_patterns('__pycache__', 'konsist', 'detekt-rules'))

    def run_new(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / 'scripts/new_client.py'), *args], capture_output=True,
                              text=True)

    def test_creates_the_client_its_platform_module_fakes_and_wiring(self) -> None:
        made = written(self.root, lambda: self.assertEqual(self.run_new('tally', 'notes').returncode, 0))
        self.assertEqual(made, [
            'app-verify/src/main/kotlin/appverify/VerifyApp.kt', 'app/module.toml',
            'app/src/main/kotlin/app/StarterApp.kt', 'features/tally/api/src/commonMain/kotlin/tally/api/TallyNotes.kt',
            'features/tally/logic/src/commonTest/kotlin/tally/logic/MemoryTallyNotes.kt',
            'fixtures/module.toml', 'fixtures/src/main/kotlin/fixtures/TallyNotesFixtures.kt', 'platform/notes/module.toml',
            'platform/notes/src/main/kotlin/platform/notes/FileTallyNotes.kt',
            'platform/notes/src/test/kotlin/platform/notes/FileTallyNotesTest.kt'])
        for path in made:
            self.assertFalse(code_owned(ANDROID_TEMPLATE, path), path)
        api = (self.root / 'features/tally/api/src/commonMain/kotlin/tally/api/TallyNotes.kt').read_text()
        for part in ('@Serializable\ndata class TallyNotesData(', 'sealed interface TallyNotesResult<out T>',
                     'data object Unreadable', 'interface TallyNotes {', 'suspend fun load(): TallyNotesResult<TallyNotesData?>'):
            self.assertIn(part, api)
        self.assertEqual((self.root / 'platform/notes/module.toml').read_text(), 'uses = ["core", "features/tally/api"]\n')
        self.assertIn('"platform/notes"]', (self.root / 'app/module.toml').read_text())
        self.assertIn('"features/tally/api", "platform/files", "platform/notes"]', (self.root / 'fixtures/module.toml').read_text())
        fixtures = (self.root / 'fixtures/src/main/kotlin/fixtures/TallyNotesFixtures.kt').read_text()
        self.assertIn('fun tallyNotesSetup(fixture: Fixture): TallyNotesSetup = when (fixture) {\n'
                      '    Fixture.Standard -> TallyNotesSetup.Empty\n    Fixture.Saved -> TallyNotesSetup.Empty\n'
                      '    Fixture.FailingSaves -> TallyNotesSetup.Empty\n    Fixture.Unreadable -> TallyNotesSetup.Empty\n}', fixtures)
        app = (self.root / 'app/src/main/kotlin/app/StarterApp.kt').read_text()
        self.assertIn('    val tallyNotes: TallyNotes by lazy { FileTallyNotes(this, Dispatchers.IO) }\n', app)
        self.assertIn('import platform.notes.FileTallyNotes\n', app)
        verify = (self.root / 'app-verify/src/main/kotlin/appverify/VerifyApp.kt').read_text()
        self.assertIn('fun tallyNotes(fixture: Fixture, reset: Boolean): TallyNotes = tallyNotesInUse ?: run {', verify)
        self.assertIn('import fixtures.tallyNotesSetup\n', verify)
        self.assertEqual(verify.count('import kotlinx.coroutines.Dispatchers\n'), 1)

    def test_an_application_class_without_a_body_gets_one(self) -> None:
        app = self.root / 'app/src/main/kotlin/app/StarterApp.kt'
        app.write_text('package app\n\nimport android.app.Application\n\n/** The root. */\nclass StarterApp : Application()\n')
        self.assertEqual(self.run_new('tally', 'notes').returncode, 0)
        self.assertEqual(app.read_text(), 'package app\n\nimport android.app.Application\nimport kotlinx.coroutines.Dispatchers\n'
                         'import platform.notes.FileTallyNotes\nimport tally.api.TallyNotes\n\n/** The root. */\n'
                         'class StarterApp : Application() {\n'
                         '    val tallyNotes: TallyNotes by lazy { FileTallyNotes(this, Dispatchers.IO) }\n}\n')

    def test_refuses_a_client_whose_names_are_taken(self) -> None:
        before = files_in(self.root)
        taken = self.run_new('tally', 'store')  # tally's api already declares TallyStore, and both apps a tallyStore
        self.assertEqual(taken.returncode, 1)
        self.assertIn('features/tally/api/src/commonMain/kotlin/tally/api/Tally.kt (it declares TallyStore)', taken.stderr)
        self.assertEqual(files_in(self.root), before)

    def test_fixtures_with_arguments_and_an_application_with_more_supertypes(self) -> None:
        fixtures = self.root / 'fixtures/src/main/kotlin/fixtures/Fixtures.kt'
        fixtures.write_text(fixtures.read_text().replace('enum class Fixture {', 'enum class Fixture(val strength: Int = 8, val sound: Boolean = true) {')
                            .replace('    Standard,', '    Standard(8, true), // "a quote in a comment\n    /** https://example.test */').replace('    Saved,', '    Saved(strength = 3) {\n        override fun toString() = "s"\n    },'))
        app = self.root / 'app/src/main/kotlin/app/StarterApp.kt'
        app.write_text(app.read_text().replace('class StarterApp : Application() {', 'class StarterApp : Application(),\n    Comparable<List<StarterApp>> {\n    override fun compareTo(other: List<StarterApp>) = 0\n'))
        self.assertEqual(self.run_new('tally', 'notes').returncode, 0)
        setup = (self.root / 'fixtures/src/main/kotlin/fixtures/TallyNotesFixtures.kt').read_text()
        self.assertIn('    Fixture.Standard -> TallyNotesSetup.Empty\n    Fixture.Saved -> TallyNotesSetup.Empty\n', setup)
        self.assertNotIn('Fixture.true', setup)
        self.assertIn('class StarterApp : Application(),\n    Comparable<List<StarterApp>> {\n    val tallyNotes: TallyNotes by lazy',
                      app.read_text())

    def test_refuses_and_writes_nothing_without_a_feature_fixtures_or_an_application(self) -> None:
        before = files_in(self.root)
        missing = self.run_new('battle', 'store')
        self.assertEqual(missing.returncode, 1)
        self.assertIn("features/battle/api isn't a feature's api module", missing.stderr)
        for bad in (('tally',), ('Tally', 'store'), ('tally', 'two words')):
            self.assertEqual(self.run_new(*bad).returncode, 2, bad)
        (self.root / 'fixtures/src/main/kotlin/fixtures/Fixtures.kt').write_text('package fixtures\n')
        self.assertIn('fixtures has no `enum class Fixture', self.run_new('tally', 'notes').stderr)
        self.assertEqual({p: d for p, d in files_in(self.root).items() if not p.startswith('fixtures/')},
                         {p: d for p, d in before.items() if not p.startswith('fixtures/')})
        self.assertEqual(self.run_new('tally', 'files').returncode, 1)  # an existing platform module is fine; its file isn't
        shutil.copytree(ANDROID_TEMPLATE / 'fixtures', self.root / 'fixtures', dirs_exist_ok=True)
        self.assertEqual(self.run_new('tally', 'notes').returncode, 0)
        again = self.run_new('tally', 'notes')
        self.assertEqual(again.returncode, 1)
        self.assertIn('already exist', again.stderr)


class AndroidFeatureMapTests(unittest.TestCase):
    """The Android starter's map check (`scripts/verify.py map`), in a copy of its scripts, features, feature map and
    journeys, outside git (so the check against the base branch says there's none). Features may share a module."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for folder in ('scripts', 'features', 'feature-map', 'verify/journeys/src', 'verify/runner/src'):
            shutil.copytree(ANDROID_TEMPLATE / folder, self.root / folder, ignore=shutil.ignore_patterns('__pycache__'))
        journeys = self.root / 'verify/journeys/src/commonMain/kotlin/journeys'
        (journeys / 'HistoryJourneys.kt').write_text(
            'package journeys\n\nimport journeykit.Journey\n\nfun Journey.historyKept() {\n    val screen = launch()\n'
            '    screen.rotate()\n    screen.returnAfterProcessDeath()\n    screen.checkpoint("kept")\n}\n')
        self.run_verify('adapters')

    def run_verify(self, mode: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / 'scripts/verify.py'), mode], cwd=self.root,
                              capture_output=True, text=True)

    def entry(self, modules: str) -> None:
        (self.root / 'feature-map/history.toml').write_text(
            f'id = "history"\nsummary = "s"\nmodules = {modules}\n\n[[journeys]]\nname = "historyKept"\nproves = "p"\n')

    def test_two_features_can_name_the_same_module(self) -> None:
        self.entry('["tally"]')
        result = self.run_verify('map')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_an_id_no_journey_names_fails_even_if_a_string_mentions_it(self) -> None:
        ui = self.root / 'features/tally/api/src/commonMain/kotlin/tally/api/TallyUi.kt'
        ui.write_text(ui.read_text().replace('    val add = ', '    public val total: UiId = UiId("tally.total")\n    val add = '))
        journeys = self.root / 'verify/journeys/src/commonMain/kotlin/journeys/HistoryJourneys.kt'
        journeys.write_text(journeys.read_text().replace('checkpoint("kept")', 'checkpoint("TallyUi.total") // say \"\"\"\n    /* old: /* nested */ screen.find(TallyUi.total) */'))
        self.entry('["tally"]')
        result = self.run_verify('map')
        self.assertEqual(result.returncode, 1)
        self.assertIn('TallyUi.total isn\'t named by any journey', result.stdout)
        self.assertEqual(result.stdout.count("isn't named by any journey"), 1, result.stdout)

    def test_a_feature_naming_no_modules_fails(self) -> None:
        self.entry('[]')
        result = self.run_verify('map')
        self.assertEqual(result.returncode, 1)
        self.assertIn('[verified-features] feature-map/history.toml: `modules` is empty.', result.stdout)


class SharedModuleMapTests(unittest.TestCase):
    """The Rust and TypeScript starters' map check (`scripts/verify.py map`), in a copy of each starter outside git:
    two features may name the same module (Hexfleet's movement shared its board's module), and one naming none fails
    (rules/verified-features/<platform>/fail-feature-names-no-modules runs that through the gate)."""

    def check(self, template: Path, journey: str, modules: str) -> subprocess.CompletedProcess:
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root)
        shutil.copytree(template, root / 'app', ignore=shutil.ignore_patterns(
            '.build', '.tools', 'node_modules', 'dist', 'target', '__pycache__'))
        (root / 'app/feature-map/second.toml').write_text(
            f'id = "second"\nsummary = "s"\nmodules = {modules}\n\n[[journeys]]\nname = "{journey}"\nproves = "p"\n')
        return subprocess.run([sys.executable, 'scripts/verify.py', 'map'], cwd=root / 'app', capture_output=True,
                              text=True)

    def test_two_features_can_name_the_same_module(self) -> None:
        for template in (RUST_TEMPLATE, TS_TEMPLATE):
            with self.subTest(template.parent.name):
                result = self.check(template, 'second_works', '["tally"]')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_feature_naming_no_modules_fails(self) -> None:
        for template in (RUST_TEMPLATE, TS_TEMPLATE):
            with self.subTest(template.parent.name):
                result = self.check(template, 'second_works', '[]')
                self.assertEqual(result.returncode, 1)
                self.assertIn('[verified-features] feature-map/second.toml: `modules` is empty.', result.stdout)


class RustNewFeatureTests(unittest.TestCase):
    """The Rust starter's scripts/new_feature.py, in a copy of its scripts, crates and feature map. (That a created
    feature passes compiler, clippy, deny, arch and settings, and its test and journey fail until written, was checked
    on the starter.)"""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for folder in ('scripts', 'crates', 'feature-map'):
            shutil.copytree(RUST_TEMPLATE / folder, self.root / folder, ignore=shutil.ignore_patterns('__pycache__'))

    def run_new(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / 'scripts/new_feature.py'), *args], capture_output=True,
                              text=True)

    def test_creates_the_crate_map_entry_journey_and_the_apps_dependency(self) -> None:
        result = self.run_new('daily_notes')
        self.assertEqual(result.returncode, 0, result.stderr)
        feature = self.root / 'crates/features/daily_notes'
        manifest = tomllib.loads((feature / 'Cargo.toml').read_text())
        self.assertEqual(manifest['package']['name'], 'daily_notes')
        self.assertEqual(manifest['lints'], {'workspace': True})
        self.assertEqual(manifest['dependencies'], {'core-types': {'path': '../../core'}})
        self.assertTrue((feature / 'src/lib.rs').read_text().startswith('#![no_std]\n'))
        self.assertIn('panic!("Write this test', (feature / 'tests/daily_notes.rs').read_text())
        entry = tomllib.loads((self.root / 'feature-map/daily_notes.toml').read_text())
        self.assertEqual((entry['modules'], entry['journeys'][0]['name']), (['daily_notes'], 'daily_notes_works'))
        journeys = (self.root / 'crates/app/tests/journeys.rs').read_text()
        self.assertIn('fn tally_is_saved_across_runs()', journeys)  # the app's own journeys stay
        self.assertIn('fn daily_notes_works() {\n    let _data = data_folder("daily_notes_works");\n    panic!("Write this journey',
                      journeys)
        app = tomllib.loads((self.root / 'crates/app/Cargo.toml').read_text())
        self.assertEqual(app['dependencies']['daily_notes'], {'path': '../features/daily_notes'})
        self.assertIn('tally', app['dependencies'])

    def test_refuses_a_bad_name_and_an_existing_feature(self) -> None:
        for bad in ('Notes', 'daily-notes', 'two words', 'fn', 'core', '1notes', 'a__b', 'notes_'):
            self.assertEqual(self.run_new(bad).returncode, 2, bad)
        self.assertEqual(self.run_new('notes').returncode, 0)
        again = self.run_new('notes')
        self.assertEqual(again.returncode, 1)
        self.assertIn('crates/features/notes already exists', again.stderr)
        taken = self.run_new('files')  # the platform crate's name
        self.assertEqual(taken.returncode, 1)
        self.assertIn('a crate named `files` is already in the workspace', taken.stderr)

    def test_writes_nothing_when_a_file_it_edits_is_read_only(self) -> None:
        journeys = self.root / 'crates/app/tests/journeys.rs'
        journeys.chmod(0o444)
        self.addCleanup(journeys.chmod, 0o644)
        result = self.run_new('notes')
        self.assertEqual(result.returncode, 1)
        self.assertIn("crates/app/tests/journeys.rs can't be written", result.stderr)
        self.assertFalse((self.root / 'crates/features/notes').exists())
        self.assertFalse((self.root / 'feature-map/notes.toml').exists())

    def test_writes_nothing_when_one_edit_cant_be_made(self) -> None:
        app = self.root / 'crates/app/Cargo.toml'
        app.write_text(app.read_text().replace('[dependencies]', '[dev-dependencies]'))
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.run_new('notes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('crates/app/Cargo.toml has no [dependencies] table', result.stderr)
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, before)

    def test_in_existing_crate_adds_map_entry_journey_and_test_only(self) -> None:
        missing = self.run_new('undo-move', '--in', 'missing')
        self.assertEqual(missing.returncode, 1)
        self.assertIn("crates/features/missing isn't a feature crate", missing.stderr)
        app_before = (self.root / 'crates/app/Cargo.toml').read_text()
        made = written(self.root, lambda: self.assertEqual(self.run_new('undo-move', '--in', 'tally').returncode, 0))
        self.assertEqual(made, [
            'crates/app/tests/journeys.rs',
            'crates/features/tally/tests/undo_move.rs',
            'feature-map/undo-move.toml',
        ])
        self.assertEqual((self.root / 'crates/app/Cargo.toml').read_text(), app_before)
        entry = tomllib.loads((self.root / 'feature-map/undo-move.toml').read_text())
        self.assertEqual((entry['id'], entry['modules'], entry['journeys'][0]['name']),
                         ('undo-move', ['tally'], 'undo_move_works'))
        self.assertIn('fn undo_move_works()', (self.root / 'crates/features/tally/tests/undo_move.rs').read_text())
        self.assertIn('fn undo_move_works()', (self.root / 'crates/app/tests/journeys.rs').read_text())
        clash = self.run_new('undo_move', '--in', 'tally')
        self.assertEqual(clash.returncode, 1)
        self.assertIn('undo_move_works', clash.stderr)


class RustWorkflowTests(unittest.TestCase):
    """The Rust starter's own CI workflow runs what b-stack's CI proves on the starter (its rust job)."""

    def test_the_starter_workflow_runs_the_commands_b_stack_ci_runs(self) -> None:
        starter = (RUST_TEMPLATE / '.github/workflows/check.yml').read_text()
        ours = (ROOT / '.github/workflows/ci.yml').read_text()
        job = ours[ours.index('\n  rust:'):]
        job = job[:re.search(r'\n  [a-z-]+:\n', job[1:]).start() + 1]
        for command in ('runs-on: ubuntu-24.04', 'mkdir -p "$RUNNER_TEMP/bstack-cache"\n',
                        'echo "BSTACK_CACHE_DIR=$RUNNER_TEMP/bstack-cache" >> "$GITHUB_ENV"',
                        'run: python3 scripts/check.py\n', 'run: python3 scripts/package.py\n'):
            self.assertIn(command, starter)
            self.assertIn(command, job)


class AgentsTemplateTests(unittest.TestCase):
    """The new-project skill has the agent delete the example, so the AGENTS.md it leaves behind, the verify skill it
    points at and the stubs new_feature.py writes must not send the agent to the example's files as the pattern to
    follow (Hexfleet's AGENTS.md pointed at the tally the setup had deleted)."""

    EXAMPLE = {
        TEMPLATE: r'Targets/Settings|NotificationSettings|SettingsLogic|save-fails',
        RUST_TEMPLATE: r'tally|Tally|platform/files|FileTallyStore',
        TS_TEMPLATE: r'tally|Tally|platform/files|fileTallyStore',
        ANDROID_TEMPLATE: r'tally|Tally|StarterApp|VerifyApp|FileTallyStore|platform/files',
    }

    def test_agent_guidance_names_no_example_files(self) -> None:
        for template, pattern in self.EXAMPLE.items():
            for path in ('AGENTS.template.md', '.agents/skills/verify/SKILL.md', 'scripts/new_feature.py'):
                if not (template / path).is_file():
                    continue
                with self.subTest(starter=template.parent.name, path=path):
                    found = re.findall(pattern, (template / path).read_text())
                    self.assertEqual(found, [], f'{path} names the example the new project deletes')


class GateGuidanceTests(unittest.TestCase):
    """Gate messages that tell the agent where to put something say what the guidance they point to says. Hexfleet's
    builder followed verify's process-death message ("keep input in the model's Saved") into serializing a whole turn,
    while core/Saved.kt said data goes to a store. Each entry: the same instruction, found in the gate's message and in
    the guidance (AGENTS.template.md, or the code comment the message relies on). Change one, change the other."""

    PINS = [
        # (starter, gate file, what its message says, guidance files, what the guidance says)
        (ANDROID_TEMPLATE, 'scripts/verify.py', ("the screen's session that isn't stored anywhere else (a selection",),
         ('AGENTS.template.md', 'core/src/commonMain/kotlin/core/Saved.kt'), "session that isn't stored anywhere else"),
        (ANDROID_TEMPLATE, 'scripts/verify.py', ('Journey bodies go in verify/journeys.',), ('AGENTS.template.md',),
         '**feature-map and journeys** (feature-map/<id>.toml, verify/journeys)'),
        (ANDROID_TEMPLATE, 'arch/konsist/src/test/kotlin/bstack/konsist/ArchitectureTest.kt',
         ('Put platform work in a platform module',), ('AGENTS.template.md',), '**platform** (platform/<name>): the only I/O.'),
        (ANDROID_TEMPLATE, 'arch/konsist/src/test/kotlin/bstack/konsist/ArchitectureTest.kt',
         ("a feature's api module holds declarations only",), ('AGENTS.template.md',), '**api** (features/<name>/api): declarations only:'),
        (RUST_TEMPLATE, 'scripts/arch.py', ("Crates go in the module shape's folders (arch/shape.toml)",), ('AGENTS.template.md',),
         'module shape (arch/shape.toml'),
        (RUST_TEMPLATE, 'scripts/verify.py', ('naming it in modules, with journeys in crates/app/tests/journeys.rs that prove',),
         ('AGENTS.template.md',), 'journeys in crates/app/tests/journeys.rs'),
        (TS_TEMPLATE, 'scripts/verify.py', ("JOURNEYS = 'apps/desktop/journeys'", "journey {name} in {JOURNEYS}/ isn't in the feature map"),
         ('AGENTS.template.md',), 'journeys in apps/desktop/journeys/'),
        (TEMPLATE, 'scripts/verify.py', ('Keep bodies in Targets/AppVerifyJourneys',), ('AGENTS.template.md',),
         'journey bodies in Targets/AppVerifyJourneys'),
    ]

    @staticmethod
    def plain(text: str) -> str:
        """Text without source punctuation: string literals joined across lines, comment stars, escapes, backticks."""
        text = re.sub(r"""['"]\s*\+?\s*\n\s*\+?\s*['"]""", '', text)  # 'a ' \n 'b' and "a " +\n "b"
        text = re.sub(r'\n\s*\*\s?', ' ', text).replace("\\'", "'").replace('`', '')
        return re.sub(r'\s+', ' ', text)

    def test_gate_messages_say_what_the_guidance_says(self) -> None:
        for template, gate, said, guides, guidance in self.PINS:
            for path, texts in ((gate, said), *((g, (guidance,)) for g in guides)):
                for text in texts:
                    with self.subTest(starter=template.parent.name, file=path, text=text):
                        self.assertIn(text, self.plain((template / path).read_text()))


class AndroidReviewTests(unittest.TestCase):
    """AGENTS.md's Review section is what the agent's own reviews check, so it names every rule enforced on Android."""

    def test_the_review_section_names_every_android_rule(self) -> None:
        text = (ANDROID_TEMPLATE / 'AGENTS.template.md').read_text()
        review = text[text.index('## Review'):]
        review = review[:review.index('\n## ', 1)]
        rules = sorted(p.parent.name for p in (ROOT / 'rules').glob('*/rule.toml')
                       if 'android' in tomllib.loads(p.read_text()))
        self.assertEqual([r for r in rules if not re.search(rf'\b{re.escape(r)}\b', review)], [])
        for part in ('**blocker**', '**should**', 'caught by a gate', 'stop and report'):
            self.assertIn(part, review)


class DerivedProjectTests(unittest.TestCase):
    """scripts/derived_project.py's plans match the new-project skill, and the starter fixes the derived projects found
    hold without running one."""

    def test_every_path_the_plan_removes_is_one_the_skill_names(self) -> None:
        sys.path.insert(0, str(ROOT / 'scripts'))
        import derived_project
        skill = (ROOT / 'skills/new-project/SKILL.md').read_text()
        sections = {'ios': skill.split('## Rust')[0], 'rust': skill.split('## Rust')[1].split('## TypeScript')[0],
                    'typescript': skill.split('## TypeScript')[1].split('## Android')[0],
                    'android': skill.split('## Android')[1].split('## GitHub')[0]}
        for name, plan in derived_project.PLANS.items():
            named = set(re.findall(r'`([^`]+)`', sections[name]))
            for path in plan.remove:
                with self.subTest(platform=name, path=path):
                    # The path itself, or a folder holding it ("the tally parts of `packages/contracts`").
                    candidates = {str(Path(*Path(path).parts[:i])) for i in range(1, len(Path(path).parts) + 1)}
                    self.assertTrue(candidates & {n.rstrip('/') for n in named}, f'the skill\'s {name} section names none of {sorted(candidates)}')

    def test_platform_folders_survive_removing_the_example(self) -> None:
        # Cargo fails every gate when a workspace member glob (crates/platform/*) matches no folder, and the rule cases
        # that add a platform package SKIP when packages/platform is gone.
        for folder in (RUST_TEMPLATE / 'crates/platform', TS_TEMPLATE / 'packages/platform'):
            with self.subTest(folder=str(folder.relative_to(ROOT))):
                self.assertTrue((folder / '.gitkeep').is_file())

    def test_the_typescript_compiler_gate_leaves_out_a_package_with_no_code(self) -> None:
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root)
        shutil.copytree(TS_TEMPLATE / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(TS_TEMPLATE / 'arch', root / 'arch')
        for package, source in (('packages/fixtures', None), ('packages/features/a', 'src/index.ts'),
                                ('packages/features/b', 'src/dist/index.ts'), ('packages/features/c', 'dist/index.js')):
            (root / package).mkdir(parents=True)
            (root / package / 'tsconfig.json').write_text('{}')
            if source:
                (root / package / source).parent.mkdir(parents=True, exist_ok=True)
                (root / package / source).write_text('export {};\n')
        proc = subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, "scripts"); import check; '
                               'print(sorted(str(p.parent.relative_to(check.ROOT)) for p in check.tsconfigs()))'],
                              cwd=root, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "['packages/features/a', 'packages/features/b']")


class AndroidWorkflowTests(unittest.TestCase):
    """The Android starter's own CI workflow runs what b-stack's CI proves on the starter (its android job)."""

    def test_the_starter_workflow_runs_the_commands_b_stack_ci_runs(self) -> None:
        starter = (ANDROID_TEMPLATE / '.github/workflows/check.yml').read_text()
        ours = (ROOT / '.github/workflows/ci.yml').read_text()
        job = ours[ours.index('\n  android:'):]
        job = job[:re.search(r'\n  [a-z-]+:\n', job[1:]).start() + 1]
        for command in ('sudo udevadm trigger --name-match=kvm', 'echo "BSTACK_CACHE_DIR=$dir" >> "$GITHUB_ENV"',
                        'sudo rm -rf /usr/local/lib/android /usr/share/dotnet /opt/ghc /usr/local/.ghcup',
                        'python3 scripts/check.py --only compiler --only detekt --only lint --only konsist --only deps && exit 0',
                        'run: python3 scripts/check.py\n', 'python3 scripts/package.py\n', 'runs-on: ubuntu-24.04'):
            self.assertIn(command, starter)
            self.assertIn(command, job)


class WorktreeLayoutTests(unittest.TestCase):
    """Each starter's layout check (scripts/arch.py) in a linked git worktree, whose `.git` is a file naming the main
    checkout's git folder, not a folder. (The iOS starter has no top-level layout check.)"""

    def test_a_worktrees_git_file_is_the_projects_own(self) -> None:
        for template in (ANDROID_TEMPLATE, TS_TEMPLATE, RUST_TEMPLATE):
            with self.subTest(template.parent.name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder) / 'app'
                shutil.copytree(template, root, ignore=shutil.ignore_patterns(
                    '.build', '.tools', 'node_modules', '.gradle', '.kotlin', 'build', '__pycache__'))
                (root / '.git').write_text('gitdir: /elsewhere/.git/worktrees/app\n')
                result = subprocess.run([sys.executable, 'scripts/arch.py'], cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class HistoryTests(unittest.TestCase):
    """scripts/history.py (the verify gate's check against the base branch), in a git repo whose project is a
    subfolder, as b-stack's starters are. The same file is in the Android and TypeScript starters."""

    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo)
        self.root = self.repo / 'app'
        self.feature('notes', ['notesWork', 'notesSurviveRotation'])
        self.feature('clock', ['clockTicks'])
        (self.root / 'arch').mkdir(parents=True)
        shutil.copy2(ANDROID_TEMPLATE / 'arch/retired.toml', self.root / 'arch/retired.toml')
        self.git('init', '-q')
        self.git('add', '-A')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        sys.path.insert(0, str(ANDROID_TEMPLATE / 'scripts'))
        self.addCleanup(sys.path.remove, str(ANDROID_TEMPLATE / 'scripts'))
        import history
        self.history = history

    def git(self, *args: str) -> str:
        return subprocess.run(['git', *args], cwd=self.repo, env=ENV, check=True, capture_output=True,
                              text=True).stdout.strip()

    def feature(self, name: str, journeys: list[str], fid: str | None = None) -> None:
        (self.root / 'features' / name).mkdir(parents=True, exist_ok=True)
        (self.root / 'feature-map').mkdir(parents=True, exist_ok=True)
        (self.root / f'feature-map/{name}.toml').write_text(
            f'id = "{fid or name}"\nmodules = ["{name}"]\n' +
            ''.join(f'\n[[journeys]]\nname = "{j}"\nproves = "p"\n' for j in journeys))

    def check(self, base: str | None = '') -> list[str]:
        features = [{**__import__('tomllib').loads(p.read_text()), 'file': f'feature-map/{p.name}'}
                    for p in sorted((self.root / 'feature-map').glob('*.toml'))]
        env = {'BSTACK_BASE_REF': self.base if base == '' else base or ''}
        with mock.patch.dict(os.environ, env), mock.patch('builtins.print'):
            return self.history.removed(self.root, features, 'features')

    def test_the_starters_share_one_file(self) -> None:
        self.assertEqual((ANDROID_TEMPLATE / 'scripts/history.py').read_text(),
                         (TS_TEMPLATE / 'scripts/history.py').read_text())
        self.assertEqual((ANDROID_TEMPLATE / 'arch/retired.toml').read_text(),
                         (TS_TEMPLATE / 'arch/retired.toml').read_text())

    def test_unchanged_map_passes(self) -> None:
        self.assertEqual(self.check(), [])

    def test_a_deleted_or_renamed_journey_fails(self) -> None:
        self.feature('notes', ['notesWork'])
        found = self.check()
        self.assertEqual(len(found), 1)
        self.assertIn('journey `notesSurviveRotation` (feature-map/notes.toml on the base branch', found[0])
        self.feature('notes', ['notesWork', 'notesSurviveTurning'])
        self.assertIn('journey `notesSurviveRotation`', ''.join(self.check()))

    def test_a_retired_journey_passes(self) -> None:
        self.feature('notes', ['notesWork'])
        (self.root / 'arch/retired.toml').write_text('journeys = ["notesSurviveRotation"]\nfeatures = []\n')
        self.assertEqual(self.check(), [])

    def test_a_journey_moved_to_another_feature_passes(self) -> None:
        self.feature('notes', ['notesWork'])
        self.feature('clock', ['clockTicks', 'notesSurviveRotation'])
        self.assertEqual(self.check(), [])

    def test_a_feature_removed_with_its_modules_passes(self) -> None:
        shutil.rmtree(self.root / 'features/clock')
        (self.root / 'feature-map/clock.toml').unlink()
        self.assertEqual(self.check(), [])

    def test_a_map_entry_gone_while_its_modules_stay_fails(self) -> None:
        (self.root / 'feature-map/clock.toml').unlink()
        self.feature('notes', ['notesWork', 'notesSurviveRotation', 'clockTicks'])  # the journey moved, the entry went
        found = self.check()
        self.assertEqual(len(found), 1)
        self.assertIn('feature `clock` (feature-map/clock.toml on the base branch', found[0])
        self.assertIn('its modules (clock) are still here', found[0])
        (self.root / 'arch/retired.toml').write_text('journeys = []\nfeatures = ["clock"]\n')
        self.assertEqual(self.check(), [])

    def test_an_entry_gone_while_another_names_its_module_fails(self) -> None:
        # Features can share a module: the gone entry's journeys stay protected while the module is here, even though
        # another entry still names it.
        (self.root / 'feature-map/alarms.toml').write_text(
            'id = "alarms"\nmodules = ["clock"]\n\n[[journeys]]\nname = "alarmsRing"\nproves = "p"\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'a second feature in the clock module')
        self.base = self.git('rev-parse', 'HEAD')
        (self.root / 'feature-map/alarms.toml').unlink()
        found = self.check()
        self.assertEqual(len(found), 2)
        self.assertIn('feature `alarms` (feature-map/alarms.toml on the base branch', found[0])
        self.assertIn('its modules (clock) are still here', found[0])
        self.assertIn('journey `alarmsRing`', found[1])

    def test_an_entry_that_named_no_modules_stays_protected(self) -> None:
        (self.root / 'feature-map/alarms.toml').write_text(
            'id = "alarms"\nmodules = []\n\n[[journeys]]\nname = "alarmsRing"\nproves = "p"\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'a feature with no modules')
        self.base = self.git('rev-parse', 'HEAD')
        (self.root / 'feature-map/alarms.toml').unlink()
        found = self.check()
        self.assertEqual(len(found), 2)
        self.assertIn('it named no modules to remove with it', found[0])
        self.assertIn('journey `alarmsRing`', found[1])

    def test_a_renamed_entry_whose_modules_stay_fails(self) -> None:
        self.feature('clock', ['clockTicks'], fid='timer')
        self.assertIn('feature `clock`', ''.join(self.check()))

    def test_no_base_passes_and_a_missing_named_base_fails(self) -> None:
        self.feature('notes', ['notesWork'])
        self.assertEqual(self.check(base=None), [])  # no origin/main, no BSTACK_BASE_REF: nothing to compare
        self.assertIn('BSTACK_BASE_REF is origin/gone', ''.join(self.check(base='origin/gone')))

    def test_the_merge_base_is_the_base(self) -> None:
        # The base branch moved on (a journey added) after this branch started: compared with its tip, this branch
        # would lack that journey; compared with where it started, it lacks nothing.
        self.git('checkout', '-q', '-b', 'base-branch')
        self.feature('clock', ['clockTicks', 'clockAlarms'])
        self.git('commit', '-qam', 'a journey on the base branch')
        self.git('checkout', '-q', self.base)
        self.assertEqual(self.check(base='base-branch'), [])
        self.feature('notes', ['notesWork'])
        self.assertIn('journey `notesSurviveRotation`', ''.join(self.check(base='base-branch')))


class BranchRulesTests(unittest.TestCase):
    """scripts/branch_rules.py: CI fails unless the default branch's rules require code-owner review and the checks.
    The rules below are GET /repos/{owner}/{repo}/rules/branches/main for a repo set up as the new-project skill says
    (read 2026-11-24)."""

    RULES = [
        {'type': 'pull_request', 'parameters': {
            'required_approving_review_count': 0, 'dismiss_stale_reviews_on_push': True, 'required_reviewers': [],
            'require_code_owner_review': True, 'require_last_push_approval': False,
            'required_review_thread_resolution': False, 'require_extra_approval_for_unattributed_changes': True,
            'allowed_merge_methods': ['merge', 'squash', 'rebase']},
         'ruleset_source_type': 'Repository', 'ruleset_source': 'owner/app', 'ruleset_id': 1},
        {'type': 'required_status_checks', 'parameters': {
            'strict_required_status_checks_policy': False, 'do_not_enforce_on_create': False,
            'required_status_checks': [{'context': 'check'}]},
         'ruleset_source_type': 'Repository', 'ruleset_source': 'owner/app', 'ruleset_id': 1}]

    def setUp(self) -> None:
        sys.path.insert(0, str(ANDROID_TEMPLATE / 'scripts'))
        self.addCleanup(sys.path.remove, str(ANDROID_TEMPLATE / 'scripts'))
        import branch_rules
        self.findings = branch_rules.findings

    def test_the_starters_share_one_file(self) -> None:
        self.assertEqual((ANDROID_TEMPLATE / 'scripts/branch_rules.py').read_text(),
                         (TS_TEMPLATE / 'scripts/branch_rules.py').read_text())

    def test_the_skills_ruleset_passes(self) -> None:
        self.assertEqual(self.findings(self.RULES, ['check'], 'main'), [])

    def test_no_rules_fails_twice(self) -> None:
        found = self.findings([], ['check'], 'main')
        self.assertEqual(len(found), 2)
        self.assertIn('main doesn\'t require code-owner review', found[0])
        self.assertIn('main doesn\'t require the status checks check', found[1])

    def test_pull_requests_without_code_owner_review_fail(self) -> None:
        rules = json.loads(json.dumps(self.RULES))
        rules[0]['parameters']['require_code_owner_review'] = False
        self.assertIn('code-owner review', ''.join(self.findings(rules, ['check'], 'main')))

    def test_a_missing_check_fails(self) -> None:
        found = self.findings(self.RULES, ['check', 'installers win-x64'], 'main')
        self.assertEqual(len(found), 1)
        self.assertIn('the status checks installers win-x64', found[0])


class StarterWorkflowRulesTests(unittest.TestCase):
    """The Android and TypeScript starters' workflows check the default branch's rules (b-stack's own CI doesn't: it
    isn't a project made from a starter), and give the verify gate the pull request's base branch."""

    def test_each_starter_checks_the_rules_the_skill_sets(self) -> None:
        skill = (ROOT / 'skills/new-project/SKILL.md').read_text()
        for template, checks in ((ANDROID_TEMPLATE, ['check']),
                                 (TS_TEMPLATE, ['check', 'installers win-x64', 'installers win-arm64',
                                                'installers linux-x64', 'installers linux-arm64'])):
            workflow = (template / '.github/workflows/check.yml').read_text()
            command = 'run: python3 scripts/branch_rules.py ' + ' '.join(shlex.quote(c) for c in checks) + '\n'
            self.assertIn(command, workflow)
            self.assertIn('fetch-depth: 0', workflow)
            self.assertIn("BSTACK_BASE_REF: ${{ github.event_name == 'pull_request' && format('origin/{0}', "
                          "github.base_ref) || '' }}", workflow)
            for check in checks:
                self.assertIn('{"context":"%s"}' % check, skill)
        self.assertIn('name: installers ${{ matrix.target }}', (TS_TEMPLATE / '.github/workflows/check.yml').read_text())
        self.assertNotIn('branch_rules.py', (ROOT / '.github/workflows/ci.yml').read_text())


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



class TestIntegrityScanTests(unittest.TestCase):
    """skills/test-integrity/scan.py flags each way a diff can weaken checking, and leaves ordinary changes alone."""

    BASE = {
        'tests/test_math.py': 'def test_add():\n    assert add(1, 2) == 3\n    assert sub(3, 1) == 2\n',
        'src/app.ts': 'export const first = (xs: number[]) => xs.slice(0, 1)\n',
        'src/lib.rs': 'pub fn get(i: usize) -> u8 {\n    assert!(i < 4);\n    0\n}\n\n#[cfg(test)]\nmod tests {\n'
                      '    #[test]\n    fn gets() { prop_assert_eq!(get(1), 0); }\n}\n',
        'src/Login.kt': 'fun login(name: String) {\n    require(name.isNotEmpty())\n}\n',
        'src/view.ts': 'export const show = (user: User) => user.shouldShowBanner\n',
        'tsconfig.json': '{ "compilerOptions": { "strict": true } }\n',
        'package.json': '{\n  "scripts": { "test": "vitest run" },\n  "dependencies": { "a": "1.0.0" }\n}\n',
        'db/check.sql': '-- assert_empty(users)\nselect 1;\n',
        'tests/old_test.py': 'def test_old():\n    assert True\n',
        'tests/__snapshots__/home.png': b'\x89PNG\r\n\x1a\n\x00\x00',
        '.githooks/pre-commit': '#!/bin/sh\npython3 scripts/check.py\n',
        'scripts/check.py': 'GATES = ["compiler", "lint"]\n',
        'README.md': 'Results should be exact; assert nothing here.\n',
        'app/tests/test math.py': 'def test_mul():\n    assert mul(2, 3) == 6\n',
    }

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        for name, body in self.BASE.items():
            self.write(name, body)
        os.chmod(self.root / '.githooks/pre-commit', 0o755)
        for args in (('init', '-q', '-b', 'main'), ('add', '-A'), ('commit', '-qm', 'base')):
            self.git(*args)

    def git(self, *args: str) -> None:
        subprocess.run(['git', '-C', str(self.root), *args], check=True, env=ENV, capture_output=True)

    def write(self, name: str, body: str | bytes) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body) if isinstance(body, bytes) else path.write_text(body)

    def run_scan(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(TEST_INTEGRITY), *args], capture_output=True, text=True,
                              cwd=cwd or self.root)

    def scan(self) -> dict[str, set[str]]:
        """Each flagged file's reasons, across all its hunks."""
        proc = self.run_scan('--base', 'HEAD', '--json')
        self.assertIn(proc.returncode, (0, 1), proc.stderr)
        flags: dict[str, set[str]] = {}
        for flag in json.loads(proc.stdout)['flags']:
            flags.setdefault(flag['file'], set()).update(flag['reasons'])
        self.assertEqual(proc.returncode, 1 if flags else 0)
        return flags

    def assert_flags(self, edits: dict[str, str | bytes], expected: dict[str, list[str]]) -> None:
        for name, body in edits.items():
            self.write(name, body)
        self.assertEqual(self.scan(), {name: set(reasons) for name, reasons in expected.items()})

    def test_nothing_changed_or_ordinary_changes(self) -> None:
        self.assertEqual(self.scan(), {})
        self.assert_flags({
            'src/app.ts': 'export const rest = (xs: number[]) => xs.slice(1)\nexport const n = [1].values().drop(1)\n',
            'src/view.ts': 'export const show = (user: User) => user.shouldShowBanner && user.shouldRetry()\n'
                           'export const fetchWithRetry = (retries = 3, timeout = 5) => retries\n',
            'README.md': 'Results should match, assert or not.\n',
            'package.json': '{\n  "scripts": { "test": "vitest run" },\n  "dependencies": { "a": "1.1.0" }\n}\n',
            'scripts/check.py': 'GATES = ["compiler", "lint", "tests"]\n',
            'tests/test_new.py': 'def test_div():\n    assert div(6, 3) == 2\n',
        }, {'scripts/check.py': ['gate code removed or changed']})  # the only flag: a gate script's line changed

    def test_loosened_assertions_in_each_language(self) -> None:
        self.assert_flags({
            'tests/test_math.py': 'def test_add():\n    assert add(1, 2)\n    assert sub(3, 1) == 2\n',
            'src/lib.rs': 'pub fn get(i: usize) -> u8 {\n    0\n}\n\n#[cfg(test)]\nmod tests {\n'
                          '    fn gets() { prop_assert!(get(1) >= 0); }\n}\n',
            'src/Login.kt': 'fun login(name: String) {\n}\n',
        }, {
            'tests/test_math.py': ['test code removed or changed', 'assertion removed or changed'],
            'src/lib.rs': ['assertion removed or changed', 'test removed or renamed'],
            'src/Login.kt': ['assertion removed or changed'],
        })

    def test_test_only_assertion_forms(self) -> None:
        cases = {
            'web/a.test.ts': ('it("a", () => {\n  expect(f()).toStrictEqual({ a: 1 })\n})\n',
                              'it("a", () => {\n  expect(f()).toBeDefined()\n})\n'),
            'app/src/commonTest/kotlin/ATest.kt': ('fun a() {\n    f() shouldBe 5\n    verify { repo.save() }\n}\n',
                                                   'fun a() {\n}\n'),
            'SwiftTests/AppTests/ATests.swift': ('func testA() {\n    #expect(f() == 5)\n}\n', 'func testA() {\n}\n'),
        }
        for name, (before, _) in cases.items():
            self.write(name, before)
        self.git('add', '-A')
        self.git('commit', '-qm', 'more tests')
        for name, (_, after) in cases.items():
            self.write(name, after)
        flags = self.scan()
        for name in cases:
            self.assertIn('assertion removed or changed', flags[name], name)

    def test_skips_stubs_mocks_and_suppressions(self) -> None:
        self.assert_flags({
            'tests/test_math.py': self.BASE['tests/test_math.py'] + '\n@pytest.mark.skip\ndef test_x():\n    pytest.xfail()\n',
            'src/app.ts': '// @ts-ignore\nexport const first = (xs: number[]) => xs.slice(0, 1)\n',
            'src/lib.rs': self.BASE['src/lib.rs'] + '\n#[allow(dead_code)]\npub fn later() { todo!() }\n',
            'src/Login.kt': '@file:Suppress("unused")\n' + self.BASE['src/Login.kt'],
            'web/b.test.ts': 'vi.mock("./db")\nit.skipIf(ci)("b", () => {})\n',
            'web/c.test.ts': 'test.only("c", () => {})\n',
            'SwiftTests/AppTests/BTests.swift': '@Test(.disabled("slow")) func b() {}\n',
            'lint/conf.py': 'import x  # ruff: noqa\n',
        }, {
            'tests/test_math.py': ['skip, only or known-failure marker added'],
            'src/app.ts': ['suppression added'],
            'src/lib.rs': ['stub or not-implemented added', 'suppression added'],
            'src/Login.kt': ['suppression added'],
            'web/b.test.ts': ['skip, only or known-failure marker added', 'mock or stub added'],
            'web/c.test.ts': ['skip, only or known-failure marker added'],
            'SwiftTests/AppTests/BTests.swift': ['skip or assumption added'],
            'lint/conf.py': ['suppression added'],
        })

    def test_moved_suppression_is_not_new(self) -> None:
        self.write('src/boot.py', 'import a  # noqa: E402\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'boot')
        self.assert_flags({'src/boot.py': 'import a, b  # noqa: E402\n'}, {})

    def test_gates_package_scripts_and_ci(self) -> None:
        self.assert_flags({
            'tsconfig.json': '{ "compilerOptions": { "strict": false } }\n',
            'apps/web/vitest.config.ts': 'export default { test: { passWithNoTests: true } }\n',
            'package.json': '{\n  "scripts": { "test": "vitest run --passWithNoTests || true" },\n  "dependencies": { "a": "1.0.0" }\n}\n',
            '.github/workflows/ci.yml': 'jobs:\n  test:\n    continue-on-error: true\n',
        }, {
            'tsconfig.json': ['gate config changed'],
            'apps/web/vitest.config.ts': ['gate config added'],
            'package.json': ['retry, ignored failure or threshold added', 'gate file changed'],
            '.github/workflows/ci.yml': ['retry, ignored failure or threshold added', 'gate config added'],
        })

    def test_deletes_renames_binary_and_mode_changes(self) -> None:
        self.git('mv', 'tests/old_test.py', 'tests/old_disabled.py')
        os.chmod(self.root / '.githooks/pre-commit', 0o644)
        self.write('tests/__snapshots__/home.png', b'\x89PNG\r\n\x1a\n\x00\x01')
        self.assert_flags({}, {
            'tests/old_test.py': ['test, snapshot or gate file deleted (a rename shows as a delete and an add)'],
            '.githooks/pre-commit': ['gate config changed', 'binary or mode change (no text diff)'],
            'tests/__snapshots__/home.png': ['snapshot or golden file changed', 'binary or mode change (no text diff)'],
        })
        (self.root / 'tests/__snapshots__/home.png').unlink()
        self.assertIn('tests/__snapshots__/home.png', self.scan())

    def test_removed_line_that_looks_like_a_diff_header(self) -> None:
        # Removing "-- assert_empty(users)" shows as "--- assert_empty(users)" in the diff.
        self.assert_flags({'db/check.sql': 'select 1;\n'}, {'db/check.sql': ['assertion removed or changed']})

    def test_odd_paths_prefix_config_and_subfolder(self) -> None:
        self.git('config', 'diff.mnemonicPrefix', 'true')
        self.write('app/tests/test math.py', 'def test_mul():\n    assert mul(2, 3)\n')
        self.write('src/new.ts', '// @ts-ignore\nexport {}\n')  # untracked, outside the folder the scan runs from
        (self.root / 'tests/test_é.py').write_text('import pytest\npytest.skip("later")\n')
        proc = self.run_scan('--base', 'HEAD', '--json', cwd=self.root / 'app')
        flags = {f['file']: f['reasons'] for f in json.loads(proc.stdout)['flags']}
        self.assertEqual(set(flags), {'app/tests/test math.py', 'src/new.ts', 'tests/test_é.py'})

    def test_new_file_prints_only_matching_lines(self) -> None:
        self.write('src/big.py', 'x = 1\n' * 50 + 'import y  # type: ignore\n')
        proc = self.run_scan('--base', 'HEAD')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('src/big.py:1  [suppression added]', proc.stdout)
        self.assertIn('+ import y  # type: ignore', proc.stdout)
        self.assertNotIn('+ x = 1', proc.stdout)
        self.assertIn('51 other added line(s) not shown', proc.stdout)

    def test_ids_are_stable_and_base_defaults_to_main(self) -> None:
        self.git('checkout', '-qb', 'feature')
        self.write('src/app.ts', '// @ts-ignore\nexport const first = (xs: number[]) => xs.slice(0, 1)\n')
        first = json.loads(self.run_scan('--json').stdout)
        second = json.loads(self.run_scan('--json').stdout)
        self.assertEqual([f['id'] for f in first['flags']], [f['id'] for f in second['flags']])
        self.assertRegex(first['flags'][0]['id'], r'^T-[0-9a-f]{8}$')

    def test_errors_exit_2(self) -> None:
        proc = self.run_scan('--base', 'no-such-ref')
        self.assertEqual(proc.returncode, 2)
        self.assertIn('scan.py:', proc.stderr)
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        self.assertEqual(self.run_scan(cwd=outside).returncode, 2)
        self.write('src/latin1.py', b'x = "\xe9"\nassert x\n')
        self.write('src/feed.py', 'x = 1\x0cassert x == 1\n')  # a form feed must not split the diff line
        self.git('add', '-A')
        self.git('commit', '-qm', 'latin1')
        self.write('src/latin1.py', b'x = "\xe9"\n')
        self.write('src/feed.py', 'x = 1\n')
        self.assert_flags({}, {'src/latin1.py': ['assertion removed or changed'],
                               'src/feed.py': ['assertion removed or changed']})


if __name__ == '__main__':
    unittest.main()
