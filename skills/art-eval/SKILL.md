---
name: art-eval
description: Choose how a project's graphics get made (sprites, icons, app icons, 3D models, animation, characters, backgrounds) by measuring agent-made art against validated metrics and the owner's blind picks. Use when a project needs art, or when comparing models or methods for making it.
---

# Art eval

Agents can make good art, but which model and which method works best changes from task to task, and automatic scores miss what the owner cares about. So measure before committing to a model or method. Validated metrics decide fidelity, and the owner's blind picks decide taste.

The lessons cited below come from the art-eval trial (`~/Code/b-stack-trials/art-eval/`, 2026-11-22 to 23: 2D sprites, line and app icons, 3D ships and rocks, realistic heads, sprite animation). `DECISIONS.md` has the numbers.

Tools in this folder:

- `picks/build.py`: builds the blind pick page from a config (`picks/picks.example.toml`).
- `picks/export.py`: writes each lane's `answers.json` from the page's saved picks.
- `flaws/rank.py`: says which metrics rank planted flaws by size.

## 1. Set up the data folder

Everything large (references, renders, runs, model weights, Python environments) goes in the cache folder (`$BSTACK_CACHE_DIR` or `cache_dir` in `~/.config/b-stack/config.toml`), never the internal drive and never Git. Point tool caches there too (`HF_HOME`, `TORCH_HOME`, `XDG_CACHE_HOME`, `PIP_CACHE_DIR`). If the folder isn't available, stop and say so.

Git holds only code, plans, results and small files.

## 2. Split the work into lanes

One lane per kind of art (sprites, app icons, 3D models, animation, characters). Each lane has its own folder, `PLAN.md`, `RESULTS.md` and data folder. Work one target at a time inside a lane.

Each lane uses one or both task kinds:

- **Rebuild:** recreate a reference from images of it. Scored by distance to the reference, so it gives a real number.
- **Design:** make a new, original piece in the reference's style. Scored by the owner's picks.

References are for measuring. Shipped art must be original.

## 3. Pick references with verified licenses

- Use free assets with a license that allows this use: CC0, CC BY, ISC or MIT. Read the license on the asset's own page, not a listing.
- Reject assets tagged against AI use (Sketchfab's `noai` tag, for example), scans of public figures, and anything with an unclear license.
- Write a `SOURCE.md` next to each asset: page URL, license, credit line, download date.

## 4. Decide who judges what

Before any run, sort every property you care about into one of three:

| Property | Decided by | Examples |
|---|---|---|
| Hard requirement | A gate (a script that passes or fails) | Icon canvas and stroke rules, square and opaque app icon, no text, animation visible at game size |
| Fidelity: closer to the reference | A validated metric (step 5) | Rebuild distance, silhouette, colour error |
| Taste: which is better | The owner's blind picks (step 8) | Design, realism, whether it reads at a glance |

Never ask the owner a fidelity question. In the trial, quick blind "which is closer to the reference" picks got 1 of 6 known-answer pairs right, where the metric got 6 of 6 (3D ships lane).

Don't use an automatic score as a stand-in for taste. Style and taste checks disagreed with the owner in every lane that tried them.

## 5. Validate every metric with planted flaws

This is b-stack's fail case, applied to art. A metric that hasn't ranked known flaws is unproven.

1. List the flaw types the metric should catch: for 2D, a bite out of the shape, a shrunk wing, a colour shift; for 3D, a missing or moved part, flipped normals, wrong proportions; for animation, jitter, drift, brightness pops, loop seams, too little motion.
2. Plant each type at a small, medium and large size on every reference item, with a script.
3. Score the clean item and the three flawed copies with each metric.
4. Run `python3 flaws/rank.py scores.csv`. A metric passes a flaw type when it orders clean < small < medium < large on at least 90% of items.
5. Use a metric only for the flaw types it passes. Record its resolution (`rank.py` prints the smallest clean-to-small gap). Differences between candidates below it count as ties.

Check the planted sizes against the owner's eye too: put a few clean-vs-flawed pairs on the pick page. If they can't see a medium flaw at the use size, loosen that gate to the large size. In the trial, a medium loop seam and a duplicated frame were invisible at game size, so those gates were loosened or dropped.

Gates reject broken art but can't rank good art. In the animation lane every subject run passed every validated gate, and the gates never told two passing animations apart.

### 3D: held-back views and a gaming check

- Score image metrics only on camera views the subject never saw. Projecting the reference images onto any rough shape looks right from the cameras they came from.
- Run a gaming check: project the reference images onto a deliberately wrong shape (flat planes, an ellipsoid). It must score clearly worse on held-back views. In the ships lane the fake beat every Opus rebuild on the views the subject saw, and was clearly worst on held-back views (DreamSim 0.248 against 0.071 and 0.145).
- Cover every side with held-back views. A flaw on one side was invisible when all held-back views looked from the other.

## 6. Pre-register the bars

In the lane's `PLAN.md`, before the first scored run:

- the tuning set and the held-out set (progress counts only on held-out targets)
- what counts as better, by how much, on how many runs
- the rule for ties (step 5's resolution)

Stop a comparison once the remaining runs can't change its verdict, and record the early stop. Write any change to the plan as a dated deviation with both readings.

## 7. Run the baseline on more than one model

Subjects are fresh headless agents with no knowledge of the eval: at least Claude Opus and GPT Sol (in the trial, `claude -p --model claude-opus-5-5` and `codex exec -m gpt-6.2-sol`).

- Each run gets its own empty folder, the task text, the reference images it may see and the tools. Not the scorer, the reference model or other runs.
- Same time budget for every run in a comparison. Record model, effort, wall time and the exact task text.
- Start with the plain prompt, no method.
- Background jobs die when your turn ends. Run subjects in the foreground in chunks, or wait for them before ending the turn.

The best model differed by task in every lane: Sol won app icons (6 to 2) and explosions (3 to 0); Opus won sprite design (3 to 1), toolbar-size line icons (6 to 4) and movement (3 to 0). Running both and picking the better one is cheap, and it often beats writing a method.

## 8. Get the owner's blind picks

1. Render each candidate **at the size and in the context it will be used**: a sprite on a hex tile at game size, an app icon at about 120 px on a home screen among other icons, a line icon at 24 px in a toolbar, a game frame at 640x480. Add a bigger copy only for a closer look. Changing the judging size changed 14 of 30 line-icon answers.
2. Write the lane's pairs file: a JSON list of at most 30 `{"id", "title", "note", "x", "y"}`, where `x` and `y` are image paths (PNG, JPG, SVG, or animated WebP or GIF; about 1024 px wide at most, under 300 KB each). A title ending in `?` replaces the lane's question for that pair. Keep your own key of what `x` and `y` are; the page shows no labels.
3. Add the lane to the page config (copy `picks/picks.example.toml`) with a taste question and a `how` line that says what size to judge at.
4. Build: `python3 picks/build.py picks.toml <out>`. Sides are shuffled by a hash of lane and pair id, so they stay put between builds. Animated candidates become frame strips that the page plays on a canvas, with play, pause, half speed and 1x, 2x, 3x zoom, so playback doesn't depend on how the viewer handles animated images. Strips need Pillow.
5. Publish `<out>/index.html` as an Artifact with `img/*` as files and the `db` capability (load the `artifact-capabilities` skill for its form). Republish to the same URL for each new round. Tell the owner, then keep working on metrics while picks are pending.
6. Export: read the db collection `picks` (each doc is `<lane>__<id>` with `choice` x, y or tie), save it as JSON, then run `python3 picks/export.py picks.toml dump.json`. It writes each lane's `answers.json` as `{id: "x" | "y" | "tie"}`.

## 9. Read the results

- Metrics and picks agree on big jumps and often disagree on small steps. On heads, the method beat the baseline 7 to 0 with the metrics agreeing, but on the next step the owner preferred v1 over v2 5 to 2 where the surface metric said v2. So **the owner's picks decide design and fine steps**; metrics decide fidelity and hard requirements.
- When picks and a metric disagree, look at the pair images and find what the owner saw before changing anything.
- With a few pairs per comparison, report directions, not proof. A 5 to 2 split happens about 45% of the time by coin flip.

## 10. Improve the method only from evidence

A method is a skill file plus helper scripts given to a fresh subject. Write one only if the baseline loses on something the owner picked against.

- Write method advice from what subjects actually produced on the tuning targets, not from priors. Rock advice written in advance ("carve facets, avoid a smooth blob") fought the smooth scanned references and made both models worse.
- Add only changes tied to a defect the owner picked against, one at a time. Text built from taste checks made icons worse in all three method rounds, while passing every automatic check.
- A method that wins on rebuild can lose on design. Keep them apart (sprites: v2 for rebuild, v1 for design, 5 to 1 on design).

## 11. Animation

- Animate only what the platform doesn't provide. Use system controls (spinners, toggles, sheets) as they are and set their exposed properties; never build custom versions.
- Motion must be visible at the use size first. Early idle loops looked still to the owner at game size ("nothing's playing"); the lane then required at least 200 visibly changing pixels at game size.
- Among animations that read, the owner picks on how it looks, not on how much it moves. A plain reference with long, bright, always-on plumes beat the models' faint flicker 4 to 2 with fewer moving pixels.

## 12. Record the outcome

In the lane's `RESULTS.md`: the numbers, which model and method won each task, what worked and what didn't. Ship the winners' output from a `final/` folder. Record decisions in the project's `DECISIONS.md`.
