# b-stack: agent instructions

## Purpose

This repo is a guide for creating new apps that agents can work on safely, built on our enforcement pyramid. Lauren Tan's talk is the source material in `research/`. The guide is our own and can go beyond it.

## Layout

- `guide/`: language-neutral philosophy and pyramid layers. No platform-specific detail here.
- `playbook/`: step-by-step procedures.
- `rules/`: one file per rule in the format given in `rules/README.md`.
- `platforms/`: per-stack detail. Every rule must appear in every platform's rule-mapping table.
- `templates/`, `starter/`: starting files and starter-repo plans.
- `research/lauren-tan-video/`: source material. Keep the raw transcript unchanged.

## Writing rules

- **Test compiler and tool claims against the real toolchain** before writing them as fact, and record the version tested. Mark untested claims as untested.
- Mark each guide file's status (Draft / Partial / Stub) and keep open questions listed rather than inventing answers.
- When citing the talk, check `research/lauren-tan-video/ANALYSIS.md` or the transcript. Don't attribute our ideas to her.
- Keep it concise. Prefer tables and checklists to long prose.
- Run `python3 scripts/check_guide.py` after changing guide, rules or platform files.

## Research media

Large media (video, slide images, viewers) lives on MicroBay at `/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g`; `artifacts/` symlinks to it. Never copy media into Git or onto the internal drive. If MicroBay isn't mounted, say so. `python3 scripts/verify_artifacts.py` checks the inventory in `ARTIFACTS.json`. `research/lauren-tan-video/build_report.py` regenerates `ANALYSIS.md` from `slide-notes.json` and rewrites files on MicroBay, which changes the manifest hashes. Inspect before running it.

## Scope

Discussing, documenting and prototyping are in scope. Don't deploy, publish, install global tools, or start automated workflows without asking.
