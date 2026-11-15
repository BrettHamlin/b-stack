# Research: All Code Is Slop (Except Mine)

Source material for the guide: Lauren Tan (poteto)'s talk, [full 17:31 video](https://www.youtube.com/watch?v=O_zcc6Xl12g). Prepared November 15, 2026.

| File | Contents |
|---|---|
| [ANALYSIS.md](ANALYSIS.md) | Slide-by-slide: what each of 42 captures shows, how it works, how to apply it. **Generated** from `slide-notes.json` by `build_report.py`. |
| [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) | The first translation of her setup into an engineering plan, written before our own guide |
| [TRANSCRIPT.md](TRANSCRIPT.md), [transcript.json](transcript.json) | Raw automatic captions, 135 segments. Technical names are often wrong ("Graphbot" = Grok Bot, "TA plus" = TLA+, "PSAC" = pstack). |
| [SLIDES.md](SLIDES.md), [slides.json](slides.json) | Slide capture list |
| `extract_slides.py`, `contact_sheets.py`, `build_report.py` | Regeneration scripts. Inspect first: they overwrite derived files on MicroBay. |

## Media on MicroBay

Root: `/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g` (the repo's `artifacts/` symlink). Includes the video-only 1080p MP4, 42 slide captures, 105 overview frames, 71 transition frames, contact sheets, and an [annotated interactive viewer](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/annotated-viewer.html). Inventory with sizes and SHA-256 hashes: [ARTIFACTS.json](../../ARTIFACTS.json), checked by `scripts/verify_artifacts.py`.

## Caveats

- Capture times are reading positions, not exact slide boundaries.
- The talk gives no Dune source, CI or merge settings, agent configuration, formal models or proofs, or cost figures.
- PR counts, revert rate and performance are different measures. The revert rate is not a defect rate, and 5 of the performance metrics regressed.
- Related public source: [pstack](https://github.com/cursor/plugins/tree/main/pstack).
