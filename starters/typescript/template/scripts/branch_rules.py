"""CI's check that GitHub enforces code-owner review: the default branch's rules must require a pull request with
code-owner review, and these status checks. Without that, CODEOWNERS protects nothing: an agent's pull request that
weakens a gate merges without the owner.

Reads GET /repos/{owner}/{repo}/rules/branches/{branch} (the active rulesets' rules; Metadata: read, which every
workflow's GITHUB_TOKEN has) with $GITHUB_TOKEN, for $GITHUB_REPOSITORY and $BRANCH. Classic branch protection isn't
read: the new-project skill sets a ruleset.

Usage: python3 scripts/branch_rules.py <required check> [<required check> ...]
"""
import json
import os
import sys
import urllib.error
import urllib.request

SETUP = ('Set it up as the new-project skill says (a ruleset on the default branch: pull requests with code-owner '
         'review, these required checks, no bypass). Only the owner can; agents never change it.')


def findings(rules: list[dict], checks: list[str], branch: str) -> list[str]:
    pull = [r.get('parameters') or {} for r in rules if r.get('type') == 'pull_request']
    required = {c.get('context') for r in rules if r.get('type') == 'required_status_checks'
                for c in (r.get('parameters') or {}).get('required_status_checks', [])}
    out = []
    if not any(p.get('require_code_owner_review') for p in pull):
        out.append(f'[protected-enforcement] {branch} doesn\'t require code-owner review for pull requests, so '
                   f'CODEOWNERS protects nothing. {SETUP}')
    missing = [c for c in checks if c not in required]
    if missing:
        out.append(f'[protected-enforcement] {branch} doesn\'t require the status checks {", ".join(missing)}, so a '
                   f'pull request can merge with them failing. {SETUP}')
    return out


def fetch(repository: str, branch: str, token: str) -> list[dict]:
    request = urllib.request.Request(f'https://api.github.com/repos/{repository}/rules/branches/{branch}', headers={
        'Accept': 'application/vnd.github+json', 'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    repository, branch, token = (os.environ.get(k, '') for k in ('GITHUB_REPOSITORY', 'BRANCH', 'GITHUB_TOKEN'))
    if not (repository and branch and token):
        sys.exit('branch_rules.py: set GITHUB_REPOSITORY, BRANCH and GITHUB_TOKEN (GitHub Actions does).')
    try:
        rules = fetch(repository, branch, token)
    except urllib.error.HTTPError as error:
        sys.exit(f'branch_rules.py: GitHub answered {error.code} for {branch}\'s rules: {error.read()[:500]!r}')
    found = findings(rules, sys.argv[1:], branch)
    print('\n'.join(found) if found else f'{branch} requires code-owner review and {", ".join(sys.argv[1:])}.')
    sys.exit(1 if found else 0)
