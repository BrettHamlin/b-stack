"""Create a feature the way the module shape expects: its package, its feature-map entry and a journey to write.

  packages/features/<name>/   package.json, tsconfig.json (the feature role's), src/index.ts, tests/<name>.test.ts
  feature-map/<name>.toml     the feature and its first journey, <name>_works (snake case)
  apps/desktop/journeys/<name>.journey.ts   that journey

The package compiles and lints as created. Its test and its journey fail until you write them, with a message saying
so: a feature isn't done until both prove it works. Then run python3 scripts/check.py.

When the feature's code goes in a package another feature already has (a new rule of the same screen, such as a
board game's combat in its `battle` package), don't make a new package: give it its own map entry, journey and test in
that package with --in:
  feature-map/<id>.toml                       the feature, naming the existing package, and its journey, <id>_works
  apps/desktop/journeys/<id>.journey.ts       that journey
  packages/features/<module>/tests/<id>.test.ts   a test to write, in the existing package

Usage: python3 scripts/new_feature.py <name>                  (lowercase letters, digits and '-', starting with a letter)
       python3 scripts/new_feature.py <id> --in <module>      (<module>: an existing packages/features/<module>)
"""
from pathlib import Path
import json
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r'^[a-z][a-z0-9-]{0,39}$')


def map_entry(fid: str, module: str, journey: str) -> str:
    return f'''id = "{fid}"
summary = "Write what the {fid} feature does for the user."
modules = ["{module}"]

[[journeys]]
name = "{journey}"
proves = "Write what this journey shows working in the app."
'''


def test_stub(fid: str) -> str:
    return f'''import {{ expect, it }} from "@effect/vitest";

it("{fid} works", () => {{
  expect.unreachable("Write this test: the {fid} feature's behaviour, asserting whole values.");
}});
'''


def journey_stub(journey: str) -> str:
    return f'''import {{ expect, test }} from "vite-plus/test";

import {{ dataFolder, launch }} from "./support/app.ts";

test("{journey}", async () => {{
  const app = await launch("{journey}", await dataFolder("{journey}"));
  await app.checkpoint("opened");
  await app.close();
  expect.unreachable("Write this journey: use the feature through the Screen, as a user would, and check what they'd see.");
}});
'''


def files(name: str) -> dict[Path, str]:
    journey = f'{name.replace("-", "_")}_works'
    scope = json.loads((ROOT / 'arch/shape.json').read_text())['scope']
    package = {
        'name': f'{scope}/{name}', 'private': True, 'type': 'module', 'exports': {'.': './src/index.ts'},
        'dependencies': {f'{scope}/contracts': 'workspace:*', 'effect': '4.1.5'},
        'devDependencies': {'@effect/vitest': '4.1.5', 'vite-plus': '1.4.0'},
    }
    folder = Path('packages/features') / name
    return {
        folder / 'package.json': json.dumps(package, indent=2) + '\n',
        folder / 'tsconfig.json': '{ "extends": "../../../arch/tsconfig/feature.json" }\n',
        folder / 'src/index.ts': f'''// The {name} feature's logic: no I/O. Declare an Effect service (Context.Service) for what it needs from outside,
// implement it in a packages/platform/ package, and provide it in the composition roots.
export const feature = "{name}";
''',
        folder / f'tests/{name}.test.ts': test_stub(name),
        Path(f'feature-map/{name}.toml'): map_entry(name, name, journey),
        Path(f'apps/desktop/journeys/{name}.journey.ts'): journey_stub(journey),
    }


def files_in_module(fid: str, module: str) -> dict[Path, str]:
    journey = f'{fid.replace("-", "_")}_works'
    return {
        Path(f'feature-map/{fid}.toml'): map_entry(fid, module, journey),
        Path(f'apps/desktop/journeys/{fid}.journey.ts'): journey_stub(journey),
        Path(f'packages/features/{module}/tests/{fid}.test.ts'): test_stub(fid),
    }


def journey_taken(journey: str) -> bool:
    if not (ROOT / 'feature-map').is_dir():
        return False
    for path in (ROOT / 'feature-map').glob('*.toml'):
        try:
            entry = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError:
            continue
        if any(j.get('name') == journey for j in entry.get('journeys', [])):
            return True
    return False


def write_planned(planned: dict[Path, str], journey: str, extra: Path | None = None) -> int:
    taken = [str(path) for path in planned if (ROOT / path).exists()]
    if extra is not None and (ROOT / extra).exists():
        taken.insert(0, str(extra))
    if journey_taken(journey):
        taken.append(f'journey `{journey}` in feature-map/')
    if taken:
        print(f'Not created: {", ".join(dict.fromkeys(taken))} already exist.', file=sys.stderr)
        return 1
    for path, text in planned.items():
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_text(text)
    print('\n'.join(f'created {path}' for path in planned))
    print('Next: write the logic, the test and the journey, then run python3 scripts/check.py.')
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == '--in' and NAME.match(argv[0]) and NAME.match(argv[2]):
        fid, module = argv[0], argv[2]
        if not (ROOT / 'packages/features' / module / 'package.json').is_file():
            found = sorted(p.parent.name for p in (ROOT / 'packages/features').glob('*/package.json'))
            print(f'Not created: packages/features/{module} isn\'t a feature package '
                  f'(there are: {", ".join(found) or "none"}). For a feature with a package of its own, run '
                  'python3 scripts/new_feature.py <name>.', file=sys.stderr)
            return 1
        return write_planned(files_in_module(fid, module), f'{fid.replace("-", "_")}_works')
    if len(argv) != 1 or not NAME.match(argv[0]):
        print(__doc__, file=sys.stderr)
        return 2
    name = argv[0]
    return write_planned(files(name), f'{name.replace("-", "_")}_works', Path('packages/features') / name)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
