"""Create a feature the way the module shape expects: its crate, its feature-map entry and a journey to write.

  crates/features/<name>/            the feature crate: `no_std` logic (src/lib.rs), the workspace lints, the core
                                     crate as its one dependency, and a test to write (tests/<name>.rs)
  feature-map/<name>.toml            the feature and its first journey, <name>_works
  crates/app/tests/journeys.rs       that journey, added at the end
  crates/app/Cargo.toml              the app depends on the feature, so it can wire it in

Every edit is checked before any file is written: nothing is created if one can't be made. Everything builds and
passes clippy, deny, arch and settings as created. The test and the journey fail until you write them, with a message
saying so: a feature isn't done until both prove it works. The app doesn't use the feature until you wire it into
crates/app/src/main.rs (code-owned). Then run python3 scripts/check.py.

When the feature's code goes in a crate another feature already has (a new rule of the same screen, such as a
board game's combat in its `battle` crate), don't make a new crate: give it its own map entry, journey and test in
that crate with --in:
  feature-map/<id>.toml                      the feature, naming the existing crate, and its journey, <id>_works
  crates/app/tests/journeys.rs               that journey, added at the end
  crates/features/<module>/tests/<id>.rs     a test to write, in the existing crate

Usage: python3 scripts/new_feature.py <name>                  (lowercase letters, digits and `_`, starting with a letter:
                                                               a Rust crate name, such as `notes` or `daily_notes`)
       python3 scripts/new_feature.py <id> --in <module>      (<id>: lowercase words joined by `-` or `_`, such as
                                                               `undo-move`; <module>: an existing crates/features/<module>)
"""
from pathlib import Path
import os
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r'^[a-z][a-z0-9_]{0,29}$')
FEATURE_ID = re.compile(r'^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$')
# Keywords, and crates every Rust program can already name: a feature called one of these couldn't be used.
RESERVED = {'as', 'async', 'await', 'box', 'break', 'const', 'continue', 'crate', 'dyn', 'else', 'enum', 'extern',
            'false', 'fn', 'for', 'gen', 'if', 'impl', 'in', 'let', 'loop', 'match', 'mod', 'move', 'mut', 'pub', 'ref',
            'return', 'self', 'static', 'struct', 'super', 'trait', 'true', 'try', 'type', 'unsafe', 'use', 'where',
            'while', 'yield', 'abstract', 'become', 'do', 'final', 'macro', 'override', 'priv', 'typeof', 'unsized',
            'virtual', 'alloc', 'core', 'std', 'test', 'proc_macro'}
JOURNEYS = Path('crates/app/tests/journeys.rs')
APP = Path('crates/app/Cargo.toml')
STUB = 'Write this journey'


def map_entry(fid: str, module: str, journey_name: str) -> str:
    return f'''id = "{fid}"
summary = "Write what the {fid} feature does for the user."
modules = ["{module}"]

[[journeys]]
name = "{journey_name}"
proves = "Write what this journey shows working in the app."
'''


def test_stub(fid: str, fn_name: str) -> str:
    return f'''#![cfg(test)]

#[test]
fn {fn_name}() {{
    panic!("Write this test: the {fid} feature's behaviour, from the outside, asserting whole values.");
}}
'''


def files(name: str) -> dict[Path, str]:
    feature = Path('crates/features') / name
    return {
        feature / 'Cargo.toml': f'''[package]
name = "{name}"
version = "0.1.0"
edition.workspace = true
rust-version.workspace = true
publish.workspace = true

[dependencies]
core-types = {{ path = "../../core" }}

[lints]
workspace = true
''',
        feature / 'src/lib.rs': f'''#![no_std]
//! The {name} feature. No I/O here: what it needs from outside (a store, a clock) is a trait it defines, implemented
//! in a platform crate and passed in by the app.

/// What the app shows for the {name} feature.
pub fn summary() -> &'static str {{
    "{name}"
}}
''',
        feature / f'tests/{name}.rs': test_stub(name, f'{name}_works'),
        Path(f'feature-map/{name}.toml'): map_entry(name, name, f'{name}_works'),
    }


def files_in_module(fid: str, module: str, snake: str) -> dict[Path, str]:
    return {
        Path(f'crates/features/{module}/tests/{snake}.rs'): test_stub(fid, f'{snake}_works'),
        Path(f'feature-map/{fid}.toml'): map_entry(fid, module, f'{snake}_works'),
    }


def journey(fid: str, journey_name: str) -> str:
    return f'''
#[test]
fn {journey_name}() {{
    let _data = data_folder("{journey_name}");
    panic!("{STUB}: run the app as a user would (app(&data, &[...])) and check what they'd see from the {fid} feature.");
}}
'''


def with_dependency(text: str, name: str) -> str | None:
    """The app's Cargo.toml with the feature added to [dependencies], or None if it has no such table."""
    match = re.search(r'^\[dependencies\][ \t]*\n', text, MULTILINE := re.MULTILINE)
    if not match:
        return None
    updated = text[:match.end()] + f'{name} = {{ path = "../features/{name}" }}\n' + text[match.end():]
    try:
        parsed = tomllib.loads(updated)
    except tomllib.TOMLDecodeError:
        return None
    return updated if parsed.get('dependencies', {}).get(name) == {'path': f'../features/{name}'} else None


def packages() -> set[str]:
    """The workspace's package names, from every crate manifest (cargo may not load the workspace)."""
    found = set()
    for manifest in (ROOT / 'crates').rglob('Cargo.toml'):
        try:
            found.add(tomllib.loads(manifest.read_text())['package']['name'].replace('-', '_'))
        except (tomllib.TOMLDecodeError, KeyError):
            continue
    return found


def writable(paths: tuple[Path, ...]) -> list[str]:
    return [f'{path} can\'t be written' for path in paths if (ROOT / path).exists()
            and not os.access(ROOT / path, os.R_OK | os.W_OK | (os.X_OK if (ROOT / path).is_dir() else 0))]


def journey_problems(journey_name: str) -> list[str]:
    out = []
    journeys = ROOT / JOURNEYS
    if not journeys.is_file():
        out.append(f'{JOURNEYS} is missing')
    elif re.search(rf'^\s*fn {journey_name}\s*\(', journeys.read_text(), re.MULTILINE):
        out.append(f'{JOURNEYS} already has a journey `{journey_name}`')
    if (ROOT / 'feature-map').is_dir() and any(
        j.get('name') == journey_name for path in (ROOT / 'feature-map').glob('*.toml')
        for j in tomllib.loads(path.read_text()).get('journeys', [])
    ):
        out.append(f'the feature map already names a journey `{journey_name}`')
    return out


def problems(name: str, planned: dict[Path, str]) -> list[str]:
    folder = Path('crates/features') / name
    out = [f'{path} already exists' for path in [folder, *(p for p in planned if not p.is_relative_to(folder))]
           if (ROOT / path).exists()]
    blocked = writable((JOURNEYS, APP, Path('crates/features'), Path('feature-map')))
    if blocked:
        return out + blocked  # the checks below read these
    if name in packages():
        out.append(f'a crate named `{name}` is already in the workspace')
    out += journey_problems(f'{name}_works')
    app = (ROOT / APP).read_text() if (ROOT / APP).is_file() else ''
    if name in tomllib.loads(app).get('dependencies', {}):
        out.append(f'{APP} already depends on `{name}`')
    elif with_dependency(app, name) is None:
        out.append(f'{APP} has no [dependencies] table to add the feature to')
    return out


def add_in_module(fid: str, module: str) -> int:
    snake = fid.replace('-', '_')
    if not (ROOT / 'crates/features' / module / 'Cargo.toml').is_file():
        found = sorted(p.parent.name for p in (ROOT / 'crates/features').glob('*/Cargo.toml'))
        print(f'Not created: crates/features/{module} isn\'t a feature crate '
              f'(there are: {", ".join(found) or "none"}). For a feature with a crate of its own, run '
              'python3 scripts/new_feature.py <name>.', file=sys.stderr)
        return 1
    planned = files_in_module(fid, module, snake)
    out = [f'{path} already exists' for path in planned if (ROOT / path).exists()]
    blocked = writable((JOURNEYS, Path(f'crates/features/{module}/tests'), Path('feature-map')))
    if not blocked:
        out += journey_problems(f'{snake}_works')
    if out or blocked:
        print(f'Not created: {"; ".join(out + blocked)}.', file=sys.stderr)
        return 1
    journeys = (ROOT / JOURNEYS).read_text()
    for path, text in planned.items():
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_text(text)
    (ROOT / JOURNEYS).write_text(journeys.rstrip('\n') + '\n' + journey(fid, f'{snake}_works'))
    print('\n'.join(f'created {path}' for path in planned))
    print(f'updated {JOURNEYS}')
    print(f'Next: write the feature in crates/features/{module}/, its test '
          f'(crates/features/{module}/tests/{snake}.rs) and its journey ({JOURNEYS}, `{snake}_works`), '
          'then run python3 scripts/check.py.')
    return 0


def valid_crate_name(name: str) -> bool:
    return bool(NAME.match(name)) and name not in RESERVED and '__' not in name and not name.endswith('_')


def valid_feature_id(fid: str) -> bool:
    snake = fid.replace('-', '_')
    return bool(FEATURE_ID.match(fid)) and len(fid) <= 39 and snake not in RESERVED and '__' not in snake


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == '--in' and valid_feature_id(argv[0]) and valid_crate_name(argv[2]):
        return add_in_module(argv[0], argv[2])
    if len(argv) != 1 or not valid_crate_name(argv[0]):
        print(__doc__, file=sys.stderr)
        return 2
    name = argv[0]
    planned = files(name)
    found = problems(name, planned)
    if found:
        print(f'Not created: {"; ".join(found)}.', file=sys.stderr)
        return 1
    app = with_dependency((ROOT / APP).read_text(), name)
    journeys = (ROOT / JOURNEYS).read_text()
    for path, text in planned.items():
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_text(text)
    (ROOT / JOURNEYS).write_text(journeys.rstrip('\n') + '\n' + journey(name, f'{name}_works'))
    (ROOT / APP).write_text(app)
    print('\n'.join(f'created {path}' for path in planned))
    print(f'updated {JOURNEYS}\nupdated {APP}')
    print(f'Next: write the feature, its test (crates/features/{name}/tests/{name}.rs) and its journey '
          f'({JOURNEYS}, `{name}_works`), wire it into crates/app/src/main.rs (code-owned), and run '
          'python3 scripts/check.py.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
