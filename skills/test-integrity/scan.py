#!/usr/bin/env python3
"""List the places a change could have weakened a repo's tests or gates.

Deterministic, no model. It compares the working tree (committed or not, plus
untracked files) with a base commit and prints one flag per diff hunk that:

- removes or changes code in a test file, adds an early return, catch, fake
  timer or timeout to an existing test, or deletes or renames a test file;
- removes an assertion or test declaration anywhere (production asserts are
  guards too);
- adds a skip, `.only`, known-failure or assumption marker, a stub
  (`todo!()`, `NotImplementedError`), a mock, or (in a test, CI or gate file) a
  retry, flaky marker, ignored failure or threshold;
- adds a suppression comment or attribute (`@ts-ignore`, `# noqa`, `#[allow(`);
- changes, adds or deletes a gate file (lint, compiler, test runner, coverage,
  CI, hook or b-stack gate config);
- changes or deletes a snapshot or golden file.

Exit 0: nothing flagged. Exit 1: flags printed. Exit 2: usage or git error.
A flag is a question, not a verdict. The judge in SKILL.md rules on each one.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import PurePosixPath


class ScanError(Exception):
    pass


ASSERTION = re.compile(
    r'[Aa]ssert|#expect\b|#require\b|XCTFail|XCTUnwrap|\bt\.(?:Error|Fatal)\w*\(|\bfail\s*\(|'
    r'\b(?:panic|unreachable)!|\bprecondition\w*\s*\(|\b(?:check|checkNotNull|requireNotNull)\s*\(|'
    r'\bpytest\.raises\b|@should_panic')
TEST_ONLY_ASSERTION = re.compile(  # too common in production code to flag there
    r'\bexpect\w*\s*\(|\.to[A-Z]\w*\s*\(|\.not\.|\bshould\w*\b|\bverify\w*\s*[({]|\brequire\s*\(')
KOTLIN_REQUIRE = re.compile(r'\brequire\s*\(')
TEST_DECL = re.compile(
    r'\bdef test\w*|\bfn test\w*|#\[(?:\w+::)?test\b|@Test\b|\bfunc test\w*|@ParameterizedTest|\bproptest!|'
    r'\b(?:it|test|describe|context|specify|suite)(?:\.\w+)*\s*\(')
SKIP = re.compile(
    r'\b(?:it|test|describe|context|suite|specify)(?:\.\w+)*\.(?:skip\w*|only|todo|fixme|fails|failing|runIf)\b|'
    r'\bx(?:it|describe|test)\s*\(|pytest\.(?:mark\.(?:skip\w*|xfail|flaky)|skip|xfail|importorskip)\b|'
    r'unittest\.(?:skip\w*|expectedFailure)|\bSkipTest\b|\.skipTest\s*\(|@(?:Ignore|Disabled|Flaky|FlakyTest)\b|'
    r'#\[ignore\b|#\[cfg_attr\([^]]*\bignore\b|#\[should_panic\b|XCTSkip|XCTExpectFailure|withKnownIssue')
TEST_ONLY_SKIP = re.compile(r'\.disabled\b|\.enabled\s*\(\s*if:\s*false|\bassume\w*\s*\(')  # SwiftUI has .disabled
STUB = re.compile(r'\b(?:todo|unimplemented)!|\bNotImplementedError\b|\bTODO\s*\(|fatalError\s*\(\s*"(?:TODO|not impl)|'
                  r'throw new Error\s*\(\s*["\'](?:TODO|not impl)', re.IGNORECASE)
MOCK = re.compile(
    r'\b(?:vi|jest)\.(?:mock|spyOn|fn)\b|@patch\b|mock\.patch|\bMagicMock\b|\bmockk\b|\bevery\s*\{|\bMockito\b|'
    r'@Mock(?:Bean|K)?\b|\bmockall\b|#\[automock\]|\bstub\w*\s*\(')
LOOSER_RUN = re.compile(
    r'\bflaky\b|\bretr(?:y|ies)\b|continue-on-error|--passWithNoTests|\|\|\s*(?:true|:)\b|--no-verify|\bset \+e\b|'
    r'--max-warnings|--exit-zero|--no-fail|\bfail_under\b|\bthreshold', re.IGNORECASE)
TEST_BYPASS = re.compile(  # added to an existing test: can end it early, swallow a failure, or change its clock
    r'^\s*return\b|\bexit\s*\(|process\.exit|\bcatch\s*[({]|^\s*except\b|\btry\s*[:{]|useFakeTimers|'
    r'\bsetConfig\s*\(|testTimeout|\bsetTimeout\s*\(|\btimeout[\w-]*\s*[:=(]', re.IGNORECASE)
RUST_DECL = re.compile(r'#\[(?:\w+::)?test\b|\bfn test\w*|\bproptest!')
TIMEOUT = re.compile(r'\btimeout[\w-]*\s*[:=(]', re.IGNORECASE)
SUPPRESSION = re.compile(  # to the end of the line, so widening an existing suppression counts as new
    r'(?:@ts-(?:ignore|expect-error|nocheck)|(?:eslint|oxlint|biome)-(?:disable|ignore)\S*|biome-ignore|'
    r'#\s*(?:(?:ruff|flake8):\s*)?noqa\S*|#\s*(?:type|pyright):\s*ignore\S*|#\s*mypy:\s*ignore\S*|pragma:\s*no\s*cover|'
    r'#!?\[(?:allow|expect)\([^)]*\)|#!?\[cfg_attr\([^]]*\ballow\b[^]]*|@(?:file:)?Suppress(?:Warnings|Lint)?\b[^\n]*|'
    r'swiftlint:disable\S*|detekt:disable|//\s*nolint\S*|#\s*pylint:\s*disable\S*|\bistanbul ignore|\bc8 ignore)[^\n]*',
    re.IGNORECASE)
PROSE = ('.md', '.txt', '.rst', '.adoc')
DATA = ('.toml', '.json', '.yml', '.yaml', '.lock', '.csv', '.xml', '.plist', '.properties')

GATE_NAMES = (
    '.gitlab-ci.yml', '.pre-commit-config.yaml', '.eslintrc*', 'eslint.config.*', '.oxlintrc*', 'oxlint*.json',
    'biome.json*', 'tsconfig*.json', 'vite.config.*', 'vitest.config.*', 'vitest.workspace.*', 'jest.config.*',
    'playwright.config.*', 'clippy.toml', '.clippy.toml', 'deny.toml', 'rustfmt.toml', '.rustfmt.toml',
    'rust-toolchain*', '.swiftlint.yml', '.swiftformat', 'detekt*.yml', 'setup.cfg', 'tox.ini', 'pytest.ini',
    'conftest.py', '.coveragerc', 'mypy.ini', '.mypy.ini', 'ruff.toml', '.ruff.toml', 'pyproject.toml', 'Cargo.toml',
    '.golangci.y*ml', 'CODEOWNERS', 'Package.swift', 'Project.swift', 'Workspace.swift', '.harmonize.yaml',
    '*.gradle.kts', '*.gradle', 'gradle.properties', 'Makefile', 'justfile', 'tools.toml', 'AGENTS.md',
    'AGENTS.template.md', 'CLAUDE.md', 'lefthook.yml', '*baseline*', 'codecov.yml', '.codecov.yml')
CONFIG_DIRS = ('.github/workflows', '.circleci', '.githooks', '.husky', '.cargo')  # any change is a gate change
GATE_CODE_DIRS = ('arch', 'build-logic', 'Rules', 'feature-map', 'scripts', 'rules')  # flagged when lines go
PACKAGE_SCRIPT = re.compile(r'"(?:test|lint|check|typecheck|verify|build|ci|pre\w*)[^"]*"\s*:')
SNAPSHOT = re.compile(r'(?:^|/)(?:__snapshots__|snapshots?|goldens?|__golden__|approved|baselines?)/|'
                      r'\.(?:snap|golden|approved\.\w+)$|(?:^|/)expected[^/]*$', re.IGNORECASE)
TEST_DIRS = {'test', 'tests', '__tests__', 'spec', 'specs', 'e2e', 'journeys', 'testfixtures', 'fixtures'}
TEST_NAME = re.compile(r'(?:^test_.*\.py|_test\.(?:py|go|rs|exs?)|\.(?:test|spec)\.[cm]?[jt]sx?|Tests?\.swift|'
                       r'Tests?\.kt|Tests?\.java|_tests?\.rs|_spec\.rb|^tests?\.rs|^conftest\.py)$')


def is_test_file(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(TEST_NAME.search(parts[-1])) or any(
        p.lower() in TEST_DIRS or p.endswith(('Tests', 'Test')) for p in parts[:-1])


def in_dirs(path: str, dirs: tuple[str, ...]) -> bool:
    folder = '/' + '/'.join(PurePosixPath(path).parts[:-1]) + '/'
    return any(f'/{d}/' in folder for d in dirs)


def is_config_file(path: str) -> bool:
    """Gate configuration: any change, even an addition, can relax what is checked."""
    return (any(fnmatch.fnmatch(PurePosixPath(path).name, g) for g in GATE_NAMES) or in_dirs(path, CONFIG_DIRS)
            or (path.endswith(DATA) and in_dirs(path, GATE_CODE_DIRS)))


def is_gate_file(path: str) -> bool:
    return is_config_file(path) or in_dirs(path, GATE_CODE_DIRS)


@dataclass
class Hunk:
    line: int  # first line in the new file (the old file for a deletion)
    context: list[str] = field(default_factory=list)  # the lines just above it in the new file, for its id
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)


@dataclass
class FileDiff:
    path: str
    status: str  # M, A, D, T (type change); an untracked file is A
    hunks: list[Hunk] = field(default_factory=list)
    tests_from: int = 0  # a Rust file's first `#[cfg(test)]` line: hunks from there on are test code


def git(repo: str, *args: str) -> str:
    proc = subprocess.run(['git', '-C', repo, *args],
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise ScanError(f'git {" ".join(args)} failed: {proc.stderr.strip()}')
    return proc.stdout


def default_base(repo: str) -> str:
    head = subprocess.run(['git', '-C', repo, 'symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD'],
                          capture_output=True, text=True).stdout.strip()
    candidates = [head.removeprefix('refs/remotes/')] if head else []
    for ref in [*candidates, 'origin/main', 'origin/master', 'main', 'master']:
        proc = subprocess.run(['git', '-C', repo, 'merge-base', 'HEAD', ref], capture_output=True, text=True)
        if proc.returncode == 0:
            return proc.stdout.strip()
    raise ScanError('no default branch found; pass --base')


HUNK_HEAD = re.compile(r'^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@')


def parse_hunks(text: str, deleted: bool) -> list[Hunk]:
    hunks: list[Hunk] = []
    for line in text.split('\n'):
        if match := HUNK_HEAD.match(line):
            hunks.append(Hunk(line=int(match.group(1) if deleted else match.group(2))))
        elif hunks and line.startswith('-'):
            hunks[-1].removed.append(line[1:])
        elif hunks and line.startswith('+'):
            hunks[-1].added.append(line[1:])
    return hunks


def changed_files(repo: str, base: str) -> list[FileDiff]:
    """Every changed path, renames split into a delete and an add, binary and mode-only changes included."""
    out = git(repo, 'diff', '--name-status', '-z', '--no-renames', base)
    fields = out.split('\0')
    files = []
    for status, path in zip(fields[0::2], fields[1::2]):
        if not path:
            continue
        diff = git(repo, 'diff', '--no-color', '--no-ext-diff', '--no-renames', '--no-textconv', '-U0',
                   '--src-prefix=a/', '--dst-prefix=b/', base, '--', path)
        files.append(with_context(repo, FileDiff(path=path, status=status[0],
                                                  hunks=parse_hunks(diff, status[0] == 'D'))))
    for path in git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split('\0'):
        if not path:
            continue
        try:
            with open(os.path.join(repo, path), encoding='utf-8', errors='replace') as handle:
                lines = handle.read().split('\n')
        except OSError:
            lines = []
        files.append(FileDiff(path=path, status='A', hunks=[Hunk(line=1, added=lines)]))
    return files


def with_context(repo: str, diff: FileDiff) -> FileDiff:
    if diff.status == 'D':
        return diff
    try:
        with open(os.path.join(repo, diff.path), encoding='utf-8', errors='replace') as handle:
            lines = handle.read().split('\n')
    except OSError:
        return diff
    for hunk in diff.hunks:
        hunk.context = lines[max(0, hunk.line - 4):max(0, hunk.line - 1)]
    if diff.path.endswith('.rs'):
        diff.tests_from = next((n for n, l in enumerate(lines, 1) if l.strip().startswith('#[cfg(test)]')), 0)
    return diff


def new_matches(pattern: re.Pattern[str], hunk: Hunk) -> list[str]:
    """Added lines with a match that the hunk's removed lines don't already have (a moved marker isn't new)."""
    before = [m.group(0) for line in hunk.removed for m in pattern.finditer(line)]
    lines = []
    for line in hunk.added:
        found = [m.group(0) for m in pattern.finditer(line)]
        if any(f not in before for f in found):
            lines.append(line)
        for f in found:
            if f in before:
                before.remove(f)
    return lines


def reasons(diff: FileDiff, hunk: Hunk) -> tuple[list[str], list[str]]:
    """The reasons a hunk is flagged, and the added lines that matched (for printing pure additions)."""
    path, found, hits = diff.path, [], []
    test = is_test_file(path) or (diff.tests_from > 0 and hunk.line >= diff.tests_from)
    gate = is_gate_file(path) or (path.endswith('package.json') and any(
        PACKAGE_SCRIPT.search(l) for l in hunk.removed + hunk.added))
    code = not path.endswith(PROSE)
    if test and hunk.removed and diff.status != 'D':
        found.append('test code removed or changed')
    if code and not path.endswith(DATA):
        kotlin = path.endswith(('.kt', '.kts'))
        if any(ASSERTION.search(l) or (test and TEST_ONLY_ASSERTION.search(l)) or (kotlin and KOTLIN_REQUIRE.search(l))
               for l in hunk.removed):
            found.append('assertion removed or changed')
        if any((test and TEST_DECL.search(l)) or (path.endswith('.rs') and RUST_DECL.search(l)) for l in hunk.removed):
            found.append('test removed or renamed')
    if code:
        for reason, pattern, applies in (
                ('skip, only or known-failure marker added', SKIP, True),
                ('skip or assumption added', TEST_ONLY_SKIP, test),
                ('stub or not-implemented added', STUB, True),
                ('mock or stub added', MOCK, test),
                ('retry, ignored failure or threshold added', LOOSER_RUN, test or gate),
                ('timeout added or changed', TIMEOUT, gate and not test),
                ('code added that can end, catch or retime a test or gate early', TEST_BYPASS,
                 (test or (gate and not is_config_file(path))) and diff.status != 'A' and not hunk.removed),
                ('suppression added', SUPPRESSION, True)):
            if applies and (lines := new_matches(pattern, hunk)):
                found.append(reason)
                hits += lines
    if is_config_file(path):
        found.append('gate config ' + {'A': 'added', 'D': 'deleted'}.get(diff.status, 'changed'))
    elif path.endswith('package.json'):
        if gate:
            found.append('gate file changed')
    elif gate and hunk.removed:
        found.append('gate code removed or changed')
    if SNAPSHOT.search(path) and diff.status != 'A':
        found.append('snapshot or golden file changed')
    return found, hits


def flag_id(path: str, hunk: Hunk) -> str:
    """Stable across reruns while the hunk and the lines above it are unchanged, so earlier verdicts can be matched.
    The same text moved under a different test gets a new id."""
    digest = hashlib.sha1('\0'.join([path, *hunk.context, '\2', *hunk.removed, '\1', *hunk.added]).encode()).hexdigest()
    return f'T-{digest[:8]}'


SHOWN = 40  # lines of a deleted file printed for the judge; it can read the rest at the base


def scan(files: list[FileDiff]) -> list[dict]:
    flags = []
    for diff in files:
        if diff.status == 'D' and (is_test_file(diff.path) or SNAPSHOT.search(diff.path) or is_gate_file(diff.path)):
            hunk = Hunk(line=1, removed=sum((h.removed for h in diff.hunks), []))
            flags.append({'id': flag_id(diff.path, hunk), 'file': diff.path, 'line': 1,
                          'reasons': ['test, snapshot or gate file deleted (a rename shows as a delete and an add)'],
                          'removed': hunk.removed[:SHOWN], 'removed_total': len(hunk.removed), 'added': []})
            continue
        hunks = diff.hunks or [Hunk(line=1)]  # binary, mode-only or type change: path checks still apply
        for hunk in hunks:
            found, hits = reasons(diff, hunk)
            if not found:
                continue
            if not diff.hunks:
                found.append('binary or mode change (no text diff)')
            added = hunk.added if hunk.removed or diff.status != 'A' or not hits else hits
            flags.append({'id': flag_id(diff.path, hunk), 'file': diff.path, 'line': hunk.line,
                          'reasons': found, 'removed': hunk.removed, 'added': added,
                          'added_total': len(hunk.added)})
    seen: dict[str, int] = {}
    for flag in flags:  # identical hunks in one file get their own ids, so each needs its own ruling
        seen[flag['id']] = seen.get(flag['id'], 0) + 1
        if seen[flag['id']] > 1:
            flag['id'] += f'-{seen[flag["id"]]}'
    return flags


def render(flags: list[dict], base: str) -> str:
    if not flags:
        return f'test-integrity: nothing flagged against {base[:12]}.'
    out = [f'test-integrity: {len(flags)} flag(s) against {base[:12]}. Each needs a judge verdict.']
    for flag in flags:
        out.append(f'\n{flag["id"]} {flag["file"]}:{flag["line"]}  [{"; ".join(flag["reasons"])}]')
        out += [f'  - {l}' for l in flag['removed']] + [f'  + {l}' for l in flag['added']]
        if (rest := flag.get('added_total', 0) - len(flag['added'])) > 0:
            out.append(f'  (new file: {rest} other added line(s) not shown)')
        if (rest := flag.get('removed_total', 0) - len(flag['removed'])) > 0:
            out.append(f'  (deleted file: {rest} more line(s); read it at the base)')
    return '\n'.join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--repo', default='.', help='any folder in the repository (default: current directory)')
    parser.add_argument('--base', help="base commit (default: merge-base with the default branch; for a stacked PR, "
                                       "pass the PR's base)")
    parser.add_argument('--json', action='store_true', help='print JSON instead of text')
    args = parser.parse_args(argv)
    try:
        repo = git(args.repo, 'rev-parse', '--show-toplevel').strip()
        base = git(repo, 'rev-parse', '--verify', '--quiet', f'{args.base}^{{commit}}').strip() if args.base \
            else default_base(repo)
        flags = scan(changed_files(repo, base))
    except ScanError as error:
        print(f'scan.py: {error}', file=sys.stderr)
        return 2
    print(json.dumps({'base': base, 'flags': flags}, indent=1) if args.json else render(flags, base))
    return 1 if flags else 0


if __name__ == '__main__':
    sys.exit(main())
