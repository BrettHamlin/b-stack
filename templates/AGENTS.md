# <App name>: agent instructions

## Before you change code

- Read `boundaries.yaml`: which module may depend on which.
- Use the existing approved APIs for <lifecycle, background work, persistence, navigation>. Don't introduce a second way to do the same thing.

## Checks

- Build: `<build command>`
- Rules: `<layer-2 check command>`
- Verify a feature: `<driver command>`; see `feature-map/`

Run all three before handing back. Include the evidence package (`templates/evidence.md` format).

## Never weaken enforcement

Never suppress, disable, weaken or bypass a check. That includes suppression comments, editing lint or compiler config, adding module dependencies, changing `boundaries.yaml`, allowlists or baselines, or editing CI.

**If the right fix isn't possible within the rules, stop and report:** what you were trying to do, which rule blocks it, and what you'd change. A clear report is a successful outcome.

## Don't write unrequested docs

No new markdown files, rule files or explanatory comments unless asked. Comments are for what code can't express.
