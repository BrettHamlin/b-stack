"""Tests for the starter's Python helpers that rule cases can't reach (they run outside check.py's gates).

Usage: python3 scripts/test_starter_scripts.py
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'starters/ios/template'
sys.path.insert(0, str(TEMPLATE / 'scripts'))
import handback  # noqa: E402
import paths  # noqa: E402

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


if __name__ == '__main__':
    unittest.main()
