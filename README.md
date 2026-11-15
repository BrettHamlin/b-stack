# Potato

A guide to building new apps that AI agents can work on quickly without the quality dropping. It started from Lauren Tan (poteto)'s talk [*All Code Is Slop (Except Mine)*](https://www.youtube.com/watch?v=O_zcc6Xl12g) and is organized around our own **enforcement pyramid**: push every rule as high as it can go, from "can't be written" down to "judged by a human."

## Where to start

| You want to… | Go to |
|---|---|
| Start a new app | [playbook/new-project.md](playbook/new-project.md) |
| Understand the approach | [guide/00-philosophy.md](guide/00-philosophy.md) → [guide/01-pyramid.md](guide/01-pyramid.md) |
| Turn an agent correction into a rule | [playbook/correction-loop.md](playbook/correction-loop.md) |
| Pick rules for a project | [rules/](rules/) |
| See how it applies to iOS | [platforms/ios-swift.md](platforms/ios-swift.md) |
| Copy starting files | [templates/](templates/) |
| See the planned iOS starter repo | [starter/ios/](starter/ios/) |
| Check what the talk actually said | [research/lauren-tan-video/](research/lauren-tan-video/) |

## Layout

```
guide/       the philosophy and each pyramid layer (any language)
playbook/    step-by-step: new project, correction loop
rules/       catalog of reusable rules, one file each
platforms/   how each layer and rule maps to a stack
templates/   starting files to copy into a new repo
starter/     plans for runnable starter repos (built later)
research/    the source talk: transcript, slide analysis, scripts
scripts/     checks for this repo
```

## Status

| Part | Status |
|---|---|
| Philosophy, pyramid, layers 1–2, foundation | Draft, discussed |
| Layer 3 verification | Partial; next to discuss |
| Prose, review, outer loop | Stubs |
| Rules catalog | 9 draft rules |
| iOS platform | Layer 1 verified with Swift 6.4.2; layer 2 and verification to build |
| iOS starter repo | Plan only |

## Checks

```sh
python3 scripts/check_guide.py          # rule entries complete, every rule mapped per platform, links resolve
python3 scripts/verify_artifacts.py     # research media on MicroBay is present (add --hash for full check)
```
