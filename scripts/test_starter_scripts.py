"""Tests for the starter's Python helpers that rule cases can't reach (they run outside check.py's gates).

Covers both starters: the iOS one's check record and simulator lock, and the Rust one's tool and toolchain setup.

Usage: python3 scripts/test_starter_scripts.py
"""
from pathlib import Path
import hashlib
import json
import os
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
sys.path.insert(0, str(TEMPLATE / 'scripts'))
import handback  # noqa: E402
import paths  # noqa: E402
import simulator  # noqa: E402

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


class SimulatorLockTests(unittest.TestCase):
    """Two checkouts' gates on one simulator kill each other's test runner, so in_use() makes the second wait."""

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


if __name__ == '__main__':
    unittest.main()
