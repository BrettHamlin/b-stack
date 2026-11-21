"""Create a feature: its crate, its feature-map entry and a journey stub. The new feature fails the verify gate until
its journey and map entry are written, so a feature can't be handed back without proof that it works in the app.

Creates:
  crates/features/<name>/Cargo.toml   depends on the core crate; inherits the workspace lints
  crates/features/<name>/src/lib.rs   #![no_std], ready for the logic and the traits it needs from outside
  feature-map/<name>.toml             the feature's entry, with an empty `summary` and `proves` to fill in
  crates/app/tests/journeys.rs        a `<name>_works` journey that fails until it's written

Then: write the logic, implement its traits in a platform crate, wire it into crates/app, write the journey and fill
in the map entry. `python3 scripts/check.py` passes once all of that is done.

Usage: python3 scripts/new_feature.py <name>     (lowercase letters, digits and _, starting with a letter)
"""
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
JOURNEYS = ROOT / 'crates/app/tests/journeys.rs'


def problems(name: str) -> list[str]:
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,39}', name):
        return [f'`{name}` isn\'t a feature name: use lowercase letters, digits and _, starting with a letter']
    found = []
    taken = {tomllib.loads(m.read_text()).get('package', {}).get('name') for m in (ROOT / 'crates').rglob('Cargo.toml')
             if 'target' not in m.parts}
    if (ROOT / 'crates/features' / name).exists() or name in taken or name.replace('_', '-') in taken:
        found.append(f'a crate named `{name}` already exists')
    if (ROOT / 'feature-map' / f'{name}.toml').exists():
        found.append(f'feature-map/{name}.toml already exists')
    if not JOURNEYS.is_file():
        found.append('crates/app/tests/journeys.rs is missing')
    elif re.search(rf'\bfn {name}_works\b', JOURNEYS.read_text()):
        found.append(f'a journey `{name}_works` already exists')
    if not (ROOT / 'crates/core/Cargo.toml').is_file():
        found.append('crates/core/Cargo.toml is missing')
    return found


def create(name: str) -> list[Path]:
    core = tomllib.loads((ROOT / 'crates/core/Cargo.toml').read_text())['package']['name']
    crate = ROOT / 'crates/features' / name
    (crate / 'src').mkdir(parents=True)
    (crate / 'Cargo.toml').write_text(f'''[package]
name = "{name}"
version = "0.1.0"
edition.workspace = true
rust-version.workspace = true
publish.workspace = true

[dependencies]
{core} = {{ path = "../../core" }}

[lints]
workspace = true
''')
    (crate / 'src/lib.rs').write_text(f'''#![no_std]
//! The {name} feature. No I/O here: define a trait for what it needs from outside, and implement it in a platform crate.
''')
    entry = ROOT / 'feature-map' / f'{name}.toml'
    entry.parent.mkdir(exist_ok=True)
    entry.write_text(f'''id = "{name}"
summary = ""
modules = ["{name}"]

[[journeys]]
name = "{name}_works"
proves = ""
''')
    text = JOURNEYS.read_text()
    JOURNEYS.write_text(text.rstrip('\n') + f'''

#[test]
fn {name}_works() {{
    panic!("journey stub from scripts/new_feature.py: run the app the way a user would and check that {name} works");
}}
''')
    return [crate / 'Cargo.toml', crate / 'src/lib.rs', entry, JOURNEYS]


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1].startswith('-'):
        sys.exit(__doc__)
    found = problems(sys.argv[1])
    if found:
        sys.exit('new_feature.py: ' + '; '.join(found) + '. Nothing was created.')
    for path in create(sys.argv[1]):
        print(f'wrote {path.relative_to(ROOT)}')
    print('Next: the logic, its platform crate, the wiring in crates/app, the journey and the map entry. '
          'Until then the verify gate fails.')
