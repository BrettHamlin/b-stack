---
name: art-eval
description: Choose how a project's graphics get made (sprites, icons, app icons, 3D models, animation, characters, backgrounds) by measuring agent-made art against validated metrics and the owner's blind picks, then hand the winners to the app as a pack. Use when a project needs art, when comparing models or methods for making it, or when new art involves an existing character.
---

# Art eval

Agents can make good art, but which model and which method works best changes from task to task, and automatic scores miss what the owner cares about. So measure before committing to a model or method. Validated metrics decide fidelity, and the owner's blind picks decide taste.

The lessons cited below come from the art-eval trial (`~/Code/b-stack-trials/art-eval/`, 2026-11-22 to 23: 2D sprites, line and app icons, 3D ships and rocks, realistic heads, sprite animation, and sequel art for an existing game: walk cycles, in-betweens, room colour grades, a character variant), and the Carbon follow-up (2026-11-24 to 26). `DECISIONS.md` records the decisions; [the Carbon results](references/carbon-2026-11-results.json) preserve its model versions, timing qualifications and all 115 blind answers with their hidden model mappings, without media. Keep those mappings away from subjects and unanswered pick requests.

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

References are for measuring. Shipped art must be original, or made by code from the owner's own game data (step 3).

## 3. Pick references with verified licenses

- Use free assets with a license that allows this use: CC0, CC BY, ISC or MIT. Read the license on the asset's own page, not a listing.
- Reject assets tagged against AI use (Sketchfab's `noai` tag, for example), scans of public figures, and anything with an unclear license.
- Write a `SOURCE.md` next to each asset: page URL, license, credit line, download date.

### Existing characters and refusals

Models sometimes decline to draw new art of an existing copyrighted character. In the trial, Opus declined or drew its own character instead 4 times on Larry Laffer walk targets, and Sol declined Larry 3 times. Sol also once declined an NPC it had drawn before ("would recreate specific game assets"). It was intermittent: the same models drew other Larry targets.

- When a model declines, record the model, the target and its words, and move on.
- Never reword the task, disguise the character or retry to get past it.
- Make variants of an existing character from the owner's own game data by deterministic code: a palette tint or remap, scripted pixel edits. Future Larry was a tint of his own cels, picked over two scripted edits.
- Models draw only original art.
- Keep the game data and anything made from it (renders, cels, palettes, finished variants) in the data folder, out of Git.

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

Gates reject broken art but can't rank good art. In the animation lane every subject run passed every validated gate, and the gates never told two passing animations apart. Look at real output by eye before trusting a gate's threshold: three firing gates set on simple hand-made references flagged good subject shots until they were replaced.

### Check that the metric can see the property

Passing planted flaws isn't enough. Also score a floor that does the obvious wrong thing, next to the real candidates.

- For a walk, repeat the standing cel. For in-betweening, copy the nearest key frame into the gap.
- If the floor scores as well as the candidates, the metric can't see that property. DreamSim passed every planted walk flaw, yet the repeated standing cel scored as well as or better than every subject's walk (0.037 to 0.075). It measures "looks like this character", not walking.
- Then pick metrics that measure the property itself. Walk fidelity uses leg outline (`legs_iou`), cel timing (`phase_err`), feet on the floor line (`contact_err`) and how much the legs move (`still`), each validated on planted flaws. DreamSim stays as an identity check.
- The bar is beating the floor, not only the model's own baseline. In in-betweening, a copy-first method made Opus 15% closer than its baseline but beat the copy floor on only 2 of 4 targets, and made Sol worse on every target it ran. Plain Sol beat the floor on 3 of 4 NPC targets with no method.
- For small motions, the floor can be the answer. On a small arm gesture nothing beat copying the key.

### 3D: held-back views and a gaming check

- Score image metrics only on camera views the subject never saw. Projecting the reference images onto any rough shape looks right from the cameras they came from.
- Run a gaming check: project the reference images onto a deliberately wrong shape (flat planes, an ellipsoid). It must score clearly worse on held-back views. In the ships lane the fake beat every Opus rebuild on the views the subject saw, and was clearly worst on held-back views (DreamSim 0.248 against 0.071 and 0.145).
- Cover every side with held-back views. A flaw on one side was invisible when all held-back views looked from the other.

### 3D: surface quality

A good photo texture hides lumpy geometry. On heads, held-back textured DreamSim ranked method v5 best, and the owner picked against v5 in all 4 of its pairs: its clay renders showed a bumpy scalp and a smeared nose.

- No geometric measure both passed planted flaws and agreed with the owner's picks.
- Keep held-back textured DreamSim as the primary score (it agreed with 21 of 28 picks).
- Send any method that changes geometry (stereo, sculpting, new base meshes) to the owner's picks before adopting it.
- Report a lumpiness warning: `normal_smooth` (smoothed surface normals against the reference) rising more than 0.25 degrees over the previous version on the same head.
- Candidate, not adopted: a pairwise vision-model judge on clay-only held-back images. Ask each pair in both orders and count it only when both agree. The Opus judge passed the planted tests (11 of 12, size order 6 of 6; Sol failed by one) and got all 4 v5 pairs DreamSim missed, but only 20 of 28 overall. With DreamSim breaking its ties it reached 24 of 28, a rule found after seeing the answers. Pre-register it and confirm it on fresh picks before using it.

## 6. Pre-register the bars

In the lane's `PLAN.md`, before the first scored run:

- the tuning set and the held-out set (progress counts only on held-out targets)
- what counts as better, by how much, on how many runs
- the rule for ties (step 5's resolution)
- the floors each target must beat (step 5)

Measure run-to-run spread before a bar rests on one run. Four Sol runs on one head varied 3 to 6% on most metrics and 43% on face distance, and one lucky run had looked like the best result. Differences inside the spread count as no change.

Stop a comparison once the remaining runs can't change its verdict, and record the early stop. Write any change to the plan as a dated deviation with both readings.

## 7. Run the baseline on more than one model

Subjects are fresh agents with no knowledge of the eval: at least Claude Opus, GPT Sol and Gemini Carbon. The tested versions were `claude-opus-5-5` and `gpt-6.2-sol` through their headless CLIs, and `gemini-4-carbon` with `thought_level=high` through T3 Antigravity. Record the actual version, effort and transport; report an unavailable model rather than silently dropping or replacing it.

- Each run gets its own empty folder, the task text, the reference images it may see and the tools. Not the scorer, the reference model or other runs.
- Same time budget for every run in a comparison. Record model, effort, wall time and the exact task text.
- Check deliverable timestamps against the deadline even when a run was cancelled at its budget. Late outputs are exploratory, not equal-budget results. Keep recovered earlier versions separate with timestamp/hash provenance; distinguish preserved files from deterministic replays, and also report the originally on-time subset.
- Start with the plain prompt, no method.
- Background jobs die when your turn ends. Run subjects in the foreground in chunks, or wait for them before ending the turn.

The original Opus/Sol trial's best model differed by task:

| Task | Better model, by the owner's picks unless noted |
|---|---|
| Sprite design | Opus, 3 to 1 |
| Line icons | Opus at toolbar size (24 px), 6 to 4; Sol when judged at 96 px, 9 to 0 |
| App icons | Sol, 6 to 2 |
| Explosions | Sol, 3 to 0 |
| Firing | split by ship; Opus 2 to 1 |
| Hex-to-hex movement | Opus, 3 to 0 |
| Walk cycles | Sol, 3 to 0 |
| In-betweening | Sol (by metric: beat the copy floor on 3 of 4) |
| Room colour grades | Sol passed every gate, Opus failed 3 of 6; the winner per room was split |

### Carbon follow-up: plain baselines, 2026-11-24 to 26

Carbon completed 97 active conditions with no refusals; 10 conditions were excluded under this skill. Of 17 late final deliverable sets, 16 earlier sets were recovered (7 directly, 9 by documented deterministic replay), leaving 96 timing-eligible runs: 80 originally on time plus 16 recoveries. One five-icon 48px rebuild batch remains excluded from equal-budget comparisons; its missing results are also reported with failure penalties. All animation taste candidates were originally on time. The evidence files and their location are recorded in the linked results.

The owner answered 79 static and 36 animation comparisons against the frozen Opus/Sol baselines. Each cell is **Carbon wins / opponent wins / ties**:

| Task | Carbon vs Opus | Carbon vs Sol |
|---|---:|---:|
| Ship sprites | 3 / 0 / 1 | 3 / 0 / 1 |
| Line icons | 4 / 11 / 0 | 3 / 7 / 0 |
| App icons | 3 / 3 / 0 | 0 / 6 / 0 |
| 3D ships | 3 / 0 / 0 | 3 / 0 / 0 |
| 3D rocks | 3 / 1 / 0 | 0 / 3 / 1 |
| Original head designs | 0 / 3 / 0 | 0 / 3 / 0 |
| Head rebuilds (taste) | 3 / 1 / 0 | 1 / 4 / 0 |
| Room colour grades | 1 / 0 / 0 | 1 / 3 / 0 |
| Engine idle loops | 1 / 2 / 0 | 2 / 1 / 0 |
| Explosions | 0 / 0 / 3 | 0 / 1 / 2 |
| Firing | 2 / 1 / 0 | 2 / 1 / 0 |
| Hex-to-hex movement | 1 / 2 / 0 | 1 / 1 / 1 |
| NPC walk cycles | 6 / 0 / 0 | 4 / 1 / 1 |
| **Total** | **30 / 24 / 4** | **20 / 31 / 6** |

For this sample, Carbon is a strong candidate for ship art and NPC walks, Opus for line icons, and Sol for app icons. Carbon lost all six original-head design comparisons. These small, related target sets give directions, not a universal model ranking; there was no new Opus-vs-Sol comparison. Sol generally led static rebuild fidelity, which stays separate from taste. Taste picks did not make the baseline idle loops pass the later visibility bar. Five of six explosion pairs were indistinguishable; close that round without more runs.

Comparing the models at baseline and letting the owner pick can beat writing a method. In the original trial, plain prompts also beat the lane's own hand-made references on most animation rounds: explosions 6 to 0, firing 4 to 2, movement 4 to 1. The reference won only the idle loop (4 to 2), where nothing read at game size. Treat your own references as a floor, not a target.

## 8. Get the owner's blind picks

Render each candidate **at the size and in the context it will be used**: a sprite on a hex tile at game size, an app icon at about 120 px on a home screen among other icons, a line icon at 24 px in a toolbar, a game frame at 640x480, a terrain tile as a patch of the board with pieces on it. Add a bigger copy only for a closer look. Changing the judging size changed 14 of 30 line-icon answers.

When `request_picks` is available, use the owner's **Picks inbox** instead of an inline HTML reviewer or an export/download flow. Give each question a stable id, a taste prompt and guidance, and option ids mapped privately to the original media paths. Set `display` to the intended use size; preserve normal-speed animated WebP/GIF playback. The tool shuffles options and hides their ids. It returns `pending` immediately; answers arrive later as messages in the requesting thread. Save each returned question id and option id (or tie), then decode with the private mapping. Do not wait or poll, ask for an export, or assume an option id means left or right.

Use the bundled page workflow below only when the inbox tool is unavailable:

1. Write the lane's pairs file: a JSON list of at most 30 `{"id", "title", "note", "x", "y"}`, where `x` and `y` are image paths (PNG, JPG, SVG, or animated WebP or GIF; about 1024 px wide at most, under 300 KB each). A title ending in `?` replaces the lane's question for that pair. Keep your own key of what `x` and `y` are; the page shows no labels.
2. Add the lane to the page config (copy `picks/picks.example.toml`) with a taste question and a `how` line. The `how` line says where to judge and what counts. Examples: "Watch it at 1x for a few loops; if you can't see any motion at 1x, that counts against it." "Judge realism only, not likeness to anyone." "Judge it in the 640x480 game frame at 1x."
3. Build: `python3 picks/build.py picks.toml <out>`. Sides are shuffled by a hash of lane and pair id, so they stay put between builds. Animated candidates become frame strips that the page plays on a canvas, with play, pause, half speed and 1x, 2x, 3x zoom, so playback doesn't depend on how the viewer handles animated images. Strips need Pillow.
4. Use an available, owner-authorized host with persistent answers, or keep the page local. Keep the same location across rounds. Verify the answer-return path before asking the owner to judge; do not depend on downloads or browser storage the agent cannot read. Tell the owner, then keep working on metrics while picks are pending.
5. Export saved answers (each record is `<lane>__<id>` with `choice` x, y or tie) as JSON, then run `python3 picks/export.py picks.toml dump.json`. It writes each lane's `answers.json` as `{id: "x" | "y" | "tie"}`.

Between rounds:

- Keep only unanswered pairs on the page. Move an answered round's pairs to their own file (`pairs_round1.json`, next to that round's key), or list their id prefix under `skip`.
- Give each round new pair ids (a round prefix such as `fire-01`). Saved picks are keyed by lane and id, so a reused id shows as already answered.
- Drop pairs the owner says are too alike to judge, and close that question. Idle thruster loops were closed this way.
- If the owner marks a whole round "can't tell", the candidates are all acceptable. Choose without more runs. All 22 sprite keeper, asteroid and team-colour pairs came back "can't tell".

## 9. Read the results

- Metrics and picks agree on big jumps and often disagree on small steps. On heads, the method beat the baseline 7 to 0 with the metrics agreeing, but on the next step the owner preferred v1 over v2 5 to 2 where the surface metric said v2. So **the owner's picks decide design and fine steps**; metrics decide fidelity and hard requirements.
- Taste can overrule fidelity. Walk method v2 was more faithful to the original on every walking metric, and the owner still preferred v1 3 to 1. Record both readings. Taste decides what ships.
- When picks and a metric disagree, look at the pair images and find what the owner saw before changing anything.
- With a few pairs per comparison, report directions, not proof. A 5 to 2 split happens about 45% of the time by coin flip.

## 10. Improve the method only from evidence

A method is a skill file plus helper scripts given to a fresh subject. Write one only if the baseline loses on something the owner picked against.

- Write method advice from what subjects actually produced on the tuning targets, not from priors. Rock advice written in advance ("carve facets, avoid a smooth blob") fought the smooth scanned references and made both models worse.
- Add only changes tied to a defect the owner picked against, one at a time. Text built from taste checks made icons worse in all three method rounds, while passing every automatic check.
- A method that wins on rebuild can lose on design. Keep them apart (sprites: v2 for rebuild, v1 for design, 5 to 1 on design).
- A method can help one model and hurt another. Judge it per model (step 5's in-betweening result).

## 11. Animation

- Animate only what the platform doesn't provide. Use system controls (spinners, toggles, sheets) as they are and set their exposed properties; never build custom versions.
- Motion must be visible at the use size first. Early idle loops looked still to the owner at game size ("nothing's playing"); the lane then required at least 200 visibly changing pixels at game size.
- Among animations that read, the owner picks on how it looks, not on how much it moves. A plain reference with long, bright, always-on plumes beat the models' faint flicker 4 to 2 with fewer moving pixels.

## 12. Record the outcome

In the lane's `RESULTS.md`: the numbers, which model and method won each task, what worked and what didn't, and every refusal. Ship the winners' output from a `final/` folder. Record decisions in the project's `DECISIONS.md`.

## 13. Hand the art to the app as a pack

Build one folder per drop with a script, from the lanes' `final/` folders:

- Each static piece as its source (SVG where there is one) and as PNG at 1x, 2x and 3x (`name.png`, `name@2x.png`, `name@3x.png`).
- Each animation as sprite sheets at 1x, 2x and 3x, its source frames, and a `sheet.json`: frame count, fps, whether it loops, columns per row, the frame's viewBox and where the sprite's own box sits in it, and per scale the sheet's file name and frame size in pixels. Add any positions the game needs, such as a move's destination or a shot's target.
- Every team colour, made by a recolour script from one drawn set and checked apart at use size, also under simulated colour blindness.
- A `README.md` that gives the geometry (tile shape and size in points, sprite size, which way sprites face), maps each animation to the game event that plays it and says how (loops or plays once, what shows before and after), and says where each piece came from.
- A preview image of a small board or scene with the pieces in place.

Give the app's builder agent the pack and a plain request; the README carries the details. A later drop is a new folder. The trial's builder (`sprites2d/eval/build_pack.py` in the trial repo) is tied to that game's lanes, so it isn't copied here.
