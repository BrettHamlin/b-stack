"""Check which metrics rank planted flaws by size: the test an evaluator passes before it is trusted.

Input: one row per (item, flaw type, metric) with the metric's score on the clean
item and on copies with a small, medium and large planted flaw. CSV with columns
item, flaw, metric, clean, small, medium, large; or a JSON list of objects with the
same keys.

A metric passes a flaw type when clean < small < medium < large, in the metric's
worse direction, on at least the threshold share of items (default 0.9). Ties
count as not ordered. By default a higher score is worse (a distance); name the
metrics where lower is worse (a similarity such as IoU) with --lower-is-worse.

Use a metric only for the flaw types it passes. Its resolution is the smallest
clean-to-small gap among the items it ordered on those types: smaller
differences between candidates were never shown to be real, so count them as ties.

Usage: python3 rank.py <scores.csv|scores.json> [--threshold 0.9] [--lower-is-worse m1,m2] [--json]
"""
from pathlib import Path
import argparse
import csv
import json
import sys

SIZES = ('clean', 'small', 'medium', 'large')


def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == '.json':
        rows = json.loads(path.read_text())
    else:
        with path.open(newline='') as f:
            rows = list(csv.DictReader(f))
    for i, row in enumerate(rows):
        missing = [k for k in ('item', 'flaw', 'metric', *SIZES) if k not in row or row[k] in ('', None)]
        if missing:
            raise ValueError(f'{path}: row {i + 1} is missing {", ".join(missing)}')
        for size in SIZES:
            row[size] = float(row[size])
    return rows


def ordered(row: dict, lower_is_worse: bool = False) -> bool:
    """True when the scores get strictly worse from clean to small to medium to large."""
    scores = [row[s] for s in SIZES]
    if lower_is_worse:
        scores = [-s for s in scores]
    return all(a < b for a, b in zip(scores, scores[1:]))


def evaluate(rows: list[dict], threshold: float = 0.9, lower_is_worse: frozenset[str] = frozenset()) -> list[dict]:
    """One result per (metric, flaw type): how many items it ordered, and whether that clears the threshold."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row['metric'], row['flaw']), []).append(row)
    results = []
    for (metric, flaw), group in sorted(groups.items()):
        lower = metric in lower_is_worse
        hits = [r for r in group if ordered(r, lower)]
        results.append({
            'metric': metric, 'flaw': flaw, 'ordered': len(hits), 'items': len(group),
            'passed': len(hits) >= threshold * len(group),
            'missed': sorted(str(r['item']) for r in group if r not in hits),
            'smallest_gap': min((abs(r['small'] - r['clean']) for r in hits), default=None),
        })
    return results


def resolution(results: list[dict]) -> dict[str, float]:
    """Per metric, the smallest clean-to-small gap over the flaw types it passed."""
    out: dict[str, float] = {}
    for r in results:
        if r['passed'] and r['smallest_gap'] is not None:
            out[r['metric']] = min(out.get(r['metric'], r['smallest_gap']), r['smallest_gap'])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('scores', type=Path)
    parser.add_argument('--threshold', type=float, default=0.9)
    parser.add_argument('--lower-is-worse', default='', help='comma-separated metrics where a lower score is worse')
    parser.add_argument('--json', action='store_true', help='print the results as JSON')
    args = parser.parse_args()
    try:
        rows = load_rows(args.scores)
    except (OSError, ValueError) as error:
        sys.exit(f'error: {error}')
    lower = frozenset(m for m in args.lower_is_worse.split(',') if m)
    results = evaluate(rows, args.threshold, lower)
    if args.json:
        print(json.dumps({'results': results, 'resolution': resolution(results)}, indent=2))
        return
    for r in results:
        verdict = 'PASS' if r['passed'] else 'FAIL'
        missed = f'  missed: {", ".join(r["missed"])}' if r['missed'] else ''
        print(f'{verdict}  {r["metric"]:<24} {r["flaw"]:<20} {r["ordered"]}/{r["items"]}{missed}')
    for metric, gap in sorted(resolution(results).items()):
        print(f'resolution  {metric}: {gap:.6g} (count smaller differences as ties)')


if __name__ == '__main__':
    main()
