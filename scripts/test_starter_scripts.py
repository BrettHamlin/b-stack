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

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'starters/ios/template'
sys.path.insert(0, str(TEMPLATE / 'scripts'))
import handback  # noqa: E402

ENV = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.invalid',
       'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.invalid'}


class HandbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / 'scripts').mkdir()
        shutil.copy2(TEMPLATE / 'scripts/handback.py', self.root / 'scripts/handback.py')
        shutil.copytree(TEMPLATE / '.githooks', self.root / '.githooks')
        (self.root / '.gitignore').write_text('.build\n')
        (self.root / 'App.swift').write_text('let a = 1\n')
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'core.hooksPath', '.githooks')
        self.git('add', '-A')
        self.git('commit', '-qm', 'start')

    def git(self, *args: str) -> str:
        return subprocess.run(['git', *args], cwd=self.root, env=ENV, check=True, capture_output=True, text=True).stdout

    def edit(self, text: str) -> None:
        (self.root / 'App.swift').write_text(text)

    def stop(self) -> str:
        return handback.stop(self.root, {'session_id': 's'})['status']

    def test_clean_repo_without_edits_is_unchanged(self) -> None:
        self.assertEqual(self.stop(), 'unchanged')

    def test_edit_without_a_check_is_unchecked(self) -> None:
        self.edit('let a = 2\n')
        self.assertEqual(self.stop(), 'unchecked')

    def test_full_passing_check_on_the_same_files_is_checked(self) -> None:
        self.edit('let a = 2\n')
        handback.record_check(self.root, handback.GATES, [])
        self.assertEqual(self.stop(), 'checked')

    def test_skipped_or_failed_gate_is_partial(self) -> None:
        self.edit('let a = 2\n')
        handback.record_check(self.root, ['compiler', 'swiftlint'], [])
        self.assertEqual(self.stop(), 'partial')
        self.edit('let a = 3\n')
        handback.record_check(self.root, handback.GATES, ['verify'])
        self.assertEqual(self.stop(), 'partial')

    def test_edit_after_the_check_is_unchecked(self) -> None:
        handback.record_check(self.root, handback.GATES, [])
        self.edit('let a = 2\n')
        self.assertEqual(self.stop(), 'unchecked')

    def test_new_untracked_file_counts_as_an_edit(self) -> None:
        handback.record_check(self.root, handback.GATES, [])
        (self.root / 'New.swift').write_text('let b = 1\n')
        self.assertEqual(self.stop(), 'unchecked')

    def test_no_new_edits_since_last_handback_is_unchanged(self) -> None:
        self.edit('let a = 2\n')
        self.assertEqual(self.stop(), 'unchecked')
        self.assertEqual(self.stop(), 'unchanged')

    def test_build_output_is_not_an_edit(self) -> None:
        handback.record_check(self.root, handback.GATES, [])
        (self.root / '.build' / 'log.txt').write_text('x')
        self.assertEqual(handback.verdict(self.root)[0], 'checked')

    def test_summary_leaves_out_unchanged(self) -> None:
        self.stop()
        self.edit('let a = 2\n')
        self.stop()
        handback.record_check(self.root, handback.GATES, [])
        self.edit('let a = 3\n')
        handback.record_check(self.root, handback.GATES, [])
        self.stop()
        self.assertEqual(handback.summary(self.root),
                         'hand-backs: 2  checked: 1  partial: 0  unchecked: 1  unchecked rate: 50%')
        lines = (self.root / '.build/handbacks.jsonl').read_text().splitlines()
        self.assertEqual([json.loads(line)['status'] for line in lines], ['unchanged', 'unchecked', 'checked'])

    def test_commit_hook_stamps_unchecked_commit(self) -> None:
        self.edit('let a = 2\n')
        self.git('commit', '-qam', 'Change a')
        self.assertIn('Checked: unchecked', self.git('log', '-1', '--format=%B'))

    def test_commit_hook_stamps_checked_commit_and_keeps_other_trailers(self) -> None:
        self.edit('let a = 2\n')
        handback.record_check(self.root, handback.GATES, [])
        self.git('commit', '-qam', 'Change a\n\nBody.\n\nCo-Authored-By: x <x@example.invalid>')
        trailers = self.git('log', '-1', '--format=%(trailers)')
        self.assertIn('Checked: checked', trailers)
        self.assertIn('Co-Authored-By: x', trailers)

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
