"""Write each lane's answers.json from the pick page's saved picks.

Read the published page's db collection "picks" (ArtifactData, action "list") and
save what it returns as a JSON file. Any nesting works: every object with "lane",
"pair" and "choice" fields is a saved pick. When a pair was picked more than once,
the latest "at" wins.

Each lane's answers file (the lane's "answers" in the config, by default next to
its pairs file) gets {pair id: "x" | "y" | "tie"}, sorted by id. Picks for lanes
not in the config are reported and left out.

Usage: python3 export.py <config.toml> <picks.json>
"""
from pathlib import Path
import json
import sys

from build import ConfigError, load_config

CHOICES = ('x', 'y', 'tie')


def saved_picks(dump) -> list[dict]:
    """Every object in the dump that looks like a saved pick."""
    if isinstance(dump, dict):
        if {'lane', 'pair', 'choice'} <= dump.keys():
            return [dump]
        return [p for value in dump.values() for p in saved_picks(value)]
    if isinstance(dump, list):
        return [p for value in dump for p in saved_picks(value)]
    return []


def answers_by_lane(picks: list[dict]) -> dict[str, dict[str, str]]:
    latest: dict[tuple[str, str], dict] = {}
    for p in picks:
        if p['choice'] not in CHOICES:
            raise ValueError(f'pick {p["lane"]}__{p["pair"]}: choice must be one of {CHOICES}, not {p["choice"]!r}')
        key = (str(p['lane']), str(p['pair']))
        if key not in latest or str(p.get('at', '')) >= str(latest[key].get('at', '')):
            latest[key] = p
    out: dict[str, dict[str, str]] = {}
    for (lane, pair), p in sorted(latest.items()):
        out.setdefault(lane, {})[pair] = p['choice']
    return out


def export(config_path: Path, dump_path: Path) -> dict[str, int]:
    config = load_config(config_path)
    by_lane = answers_by_lane(saved_picks(json.loads(dump_path.read_text())))
    counts = {}
    for lane in config['lane']:
        answers = by_lane.pop(lane['key'], {})
        path = Path(lane['answers'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(answers, indent=2) + '\n')
        counts[lane['key']] = len(answers)
    for lane in by_lane:
        print(f'warning: {len(by_lane[lane])} picks for lane "{lane}", which is not in the config', file=sys.stderr)
    return counts


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__.strip().splitlines()[-1])
    try:
        counts = export(Path(sys.argv[1]).resolve(), Path(sys.argv[2]))
    except (ConfigError, ValueError) as error:
        sys.exit(f'error: {error}')
    print('answers per lane:', counts)


if __name__ == '__main__':
    main()
