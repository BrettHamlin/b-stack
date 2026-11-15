# Potato

A research foundation for applying Lauren Tan (poteto)'s engineering setup to mobile, desktop, web, backend, and CLI software.

Source: [All Code Is Slop (Except Mine)](https://www.youtube.com/watch?v=O_zcc6Xl12g), full 17:31 video. The project includes the complete transcript, slide analysis, implementation guide, generation scripts, and references to every saved media artifact.

## Start here

- [Slide-by-slide analysis](/Users/atlas/Code/potato/research/lauren-tan-video/ANALYSIS.md): what each slide shows, how it works, and how we can apply it.
- [Implementation guide](/Users/atlas/Code/potato/research/lauren-tan-video/IMPLEMENTATION-GUIDE.md): architecture, enforcement, feature maps, runtime drivers, formal verification, evidence, and automation.
- [Readable transcript](/Users/atlas/Code/potato/research/lauren-tan-video/TRANSCRIPT.md) and [raw transcript JSON](/Users/atlas/Code/potato/research/lauren-tan-video/transcript.json): all 135 caption segments.
- [All selected slides](/Users/atlas/Code/potato/research/lauren-tan-video/SLIDES.md) and [slide metadata](/Users/atlas/Code/potato/research/lauren-tan-video/slides.json).
- [Annotated interactive viewer](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/annotated-viewer.html): self-contained HTML with embedded slides, notes, charts, and searchable transcript.
- [Agent instructions](/Users/atlas/Code/potato/AGENTS.md).

## Large artifacts live on MicroBay

External media root: `/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g`.

`artifacts/` links directly to that directory. The project contains references, not duplicate media. MicroBay must be mounted for these files and the viewer to open.

- 42 readable slide/build captures in `artifacts/slides/`.
- 105 full-video overview samples and 71 detected visual-transition captures in `artifacts/frames/`.
- Six overview contact sheets and four transition contact sheets.
- Original 1080p video-only MP4, yt-dlp metadata, transition extraction log, browser screenshot, slide manifest, both viewer variants, and text snapshots.
- [Complete artifact manifest](/Users/atlas/Code/potato/ARTIFACTS.json): 239 files, 121.7 MiB, with relative paths, sizes, and SHA-256 hashes.

The downloaded MP4 contains no audio track. Speech analysis used the full automatic transcript. Technical names in the captions have known errors; the analysis checks names against slides. The selected captures group repeated highlights and UI-demo frames; they are not a claim that the original deck contains exactly 42 unique slides.

## Verify the bundle

```sh
cd /Users/atlas/Code/potato
python3 scripts/verify_artifacts.py --hash
```

Python 3.11+ is required for hash verification. Set `POTATO_MEDIA_ROOT` if the media directory is relocated, then repair the `artifacts` symlink and media references as appropriate. The default keeps the user's requested MicroBay storage.

## Reproduction scripts

The original scripts are preserved under `research/lauren-tan-video/`:

- `extract_slides.py`: extracts the 42 selected captures using ffmpeg.
- `contact_sheets.py`: builds overview/transition sheets using Pillow.
- `build_report.py`: assembles Markdown analysis and both HTML viewer variants.

They use the existing MicroBay media root. Inspect before rerunning because derived captures/reports may be replaced. Requirements: Python, ffmpeg, and Pillow for contact sheets (`uv run --with pillow python ...` was used). Scripts and text are small and tracked locally; media stays external.

## Provenance

Prepared November 15, 2026, from the entire video transcript, full-video frame sampling, transition inspection, and the public pstack repository. The linked create-verification-skill source was also read as corroboration. Public repository content can evolve independently of the talk. Private implementation details and productivity claims have not been independently reproduced.

This project preserves the research without changing any application behavior. Its proposed commands, schemas, and platform designs are examples to implement in the relevant product, not already-installed infrastructure.
