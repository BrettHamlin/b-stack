"""What differs per platform for rules and their cases. Each rule.toml has one [<platform>] table per platform it's
enforced on, and its cases live in rules/<rule-id>/<platform>/<case>/; test_rules.py runs them through that
platform's starter (or --project) and check_repo.py validates them."""
from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Platform:
    name: str
    starter: Path
    gates: tuple[str, ...]  # the project's check.py gates, in order; a fail case names one as enforced_by
    pass_gates: tuple[str, ...]  # what a pass case must get through
    overlays: tuple[str, ...]  # folders a case may add files to or replace files in
    editable: tuple[str, ...]  # files a case may change with `edits` (find/replace), reset before every case
    targets: str  # the folder of modules; a case module the project doesn't have is a SKIP unless in adds_targets
    case_files: tuple[str, ...]  # globs (in a case folder): a case must have at least one match, or edits
    example: re.Pattern  # names from the starter's example feature
    example_name: str
    simulator_kinds: frozenset[str]  # case kinds ('pass' or a gate) that need a simulator
    cost: dict  # rough minutes per case kind, so the longest start first
    tools: tuple[str, ...]  # downloaded once before workers start (scripts/tools.py <name>)
    marker: str  # a file only this platform's projects have
    restamp: bool = False  # give reset files the current time: the build tool rebuilds by mtime, and copies keep theirs
    installed: tuple[str, ...] = ()  # folder names the package manager creates in the project; never copied


PLATFORMS = {
    'ios': Platform(
        name='ios', starter=ROOT / 'starters/ios/template',
        gates=('compiler', 'tuist', 'swiftlint', 'harmonize', 'tests', 'verify'),
        pass_gates=('compiler', 'tuist', 'swiftlint', 'harmonize', 'tests'),
        overlays=('Targets', 'feature-map', 'Tuist/ProjectDescriptionHelpers'), editable=('Project.swift',),
        targets='Targets',
        case_files=('Targets/*/*.swift', 'feature-map/*.toml', 'Tuist/ProjectDescriptionHelpers/*.swift'),
        example=re.compile(r'[\w.-]*(?:Settings|notification|save-fails)[\w.-]*'), example_name='Settings',
        simulator_kinds=frozenset({'pass', 'tests', 'verify'}),
        cost={'untouched': 6, 'verify': 2, 'pass': 2, 'compiler': 1, 'tests': 1, 'tuist': 0.2, 'harmonize': 0.2,
              'swiftlint': 0.1},
        tools=('tuist', 'swiftlint'), marker='Project.swift'),
    'rust': Platform(
        name='rust', starter=ROOT / 'starters/rust/template',
        gates=('compiler', 'clippy', 'deny', 'arch', 'settings', 'tests', 'verify'),
        pass_gates=('compiler', 'clippy', 'deny', 'arch', 'settings', 'tests'),
        overlays=('crates', 'feature-map', '.cargo'),
        editable=('Cargo.toml', 'Cargo.lock', 'clippy.toml', 'deny.toml', 'CODEOWNERS'),
        targets='crates',
        case_files=('crates/**/*.rs', 'crates/**/Cargo.toml', 'feature-map/*.toml', '.cargo/*.toml'),
        example=re.compile(r'[\w.-]*(?:[Tt]ally|apple|pear|Count)[\w.-]*'), example_name='tally',
        simulator_kinds=frozenset(),
        cost={'untouched': 1, 'pass': 0.5, 'compiler': 0.2, 'clippy': 0.2, 'tests': 0.3, 'verify': 0.3, 'deny': 0.1,
              'arch': 0.1, 'settings': 0.1},
        tools=('rust', 'cargo-deny'), marker='arch/shape.toml', restamp=True),
    'typescript': Platform(
        name='typescript', starter=ROOT / 'starters/typescript/template',
        gates=('compiler', 'lint', 'deps', 'arch', 'settings', 'tests', 'verify'),
        pass_gates=('compiler', 'lint', 'deps', 'arch', 'settings', 'tests'),
        overlays=('packages', 'apps', 'feature-map'),
        editable=('package.json', 'pnpm-lock.yaml', 'pnpm-workspace.yaml', 'tsconfig.base.json', 'tsconfig.effect.json',
                  'vite.config.ts', 'CODEOWNERS'),
        targets='packages',
        case_files=('packages/**/*.ts', 'packages/**/*.tsx', 'packages/**/*.json', 'apps/**/*.ts', 'apps/**/*.tsx',
                    'apps/**/*.json', 'feature-map/*.toml'),
        example=re.compile(r'[\w.-]*(?:[Tt]ally|apple|pear|Count|ItemName|StorageFailed|InvalidName)[\w.-]*'), example_name='tally',
        simulator_kinds=frozenset(),
        cost={'untouched': 0.5, 'pass': 0.2, 'verify': 0.3, 'compiler': 0.1, 'lint': 0.1, 'tests': 0.1, 'deps': 0.1,
              'arch': 0.05, 'settings': 0.05},
        tools=('node', 'pnpm'), marker='pnpm-workspace.yaml', installed=('node_modules', 'dist')),
    'android': Platform(
        name='android', starter=ROOT / 'starters/android/template',
        gates=('compiler', 'detekt', 'lint', 'konsist', 'arch', 'deps', 'settings', 'tests', 'verify', 'release'),
        pass_gates=('compiler', 'detekt', 'lint', 'konsist', 'arch', 'deps', 'settings', 'tests'),
        overlays=('core', 'core-ui', 'features', 'platform', 'fixtures', 'app', 'app-verify', 'verify', 'feature-map'),
        editable=('gradle/libs.versions.toml', 'settings.gradle.kts', 'gradle.properties', 'CODEOWNERS'),
        targets='features',
        case_files=('core/**/*', 'core-ui/**/*', 'features/**/*', 'platform/**/*', 'fixtures/**/*', 'app/**/*',
                    'app-verify/**/*', 'verify/**/*', 'feature-map/*.toml'),
        example=re.compile(r'[\w.-]*(?:[Tt]ally|apple|pear|ItemName|Stored)[\w.-]*'), example_name='tally',
        simulator_kinds=frozenset(),  # verify.py takes the emulator's lock itself (scripts/emulator.py)
        cost={'untouched': 2.5, 'verify': 1, 'release': 1.5, 'pass': 0.5, 'compiler': 0.2, 'detekt': 0.2, 'konsist': 0.2, 'lint': 0.2,
              'tests': 0.2, 'deps': 0.1, 'settings': 0.1, 'arch': 0.05},
        tools=('jdk', 'gradle', 'cmdline-tools', 'sdk'), marker='build-logic/settings.gradle.kts',
        installed=('build', '.gradle', '.kotlin')),
}


def platform_of(project: Path) -> Platform | None:
    return next((p for p in PLATFORMS.values() if (project / p.marker).is_file()), None)
