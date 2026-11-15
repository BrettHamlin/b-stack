# Potato project instructions

## Purpose

This project preserves and develops a detailed understanding of Lauren Tan (poteto)'s “All Code Is Slop (Except Mine)” talk and translates its engineering practices into software we build: mobile, desktop, web, backend services, and CLIs.

## Read first

1. README.md for the project inventory and external storage location.
2. research/lauren-tan-video/ANALYSIS.md for the slide-by-slide findings.
3. research/lauren-tan-video/IMPLEMENTATION-GUIDE.md for the proposed application.
4. The transcript and original slide captures when checking a particular claim.

## Evidence and accuracy

- Cover the entire video; do not restrict analysis to the timestamp in the original link.
- Distinguish slide observations, the speaker's reported experience, public-source corroboration, and our proposed engineering designs.
- Preserve the raw automatic transcript. Its technical-name errors are not authoritative names; explain corrections in analysis rather than silently changing the source.
- Capture timestamps are reading positions, not exact slide boundaries. The 42 selected captures include builds, not 42 asserted unique deck pages.
- PR throughput, reverted-commit percentage, and performance are different measures. Do not equate revert rate with defect rate or claim every performance measure improved.
- The talk does not provide private Dune source, complete CI/merge settings, exact agent configuration, formal models/proofs, or cost accounting. Do not invent those details.
- State the assumptions, bounds, and implementation correspondence of any future formal verification. A diagram or a passing abstract model is not proof of the entire product.

## Storage

- Keep large downloads, video, images, recordings, embedded-media HTML, and other bulky artifacts on MicroBay, as explicitly requested by the user.
- Existing media root: /Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g.
- artifacts/ is an absolute symlink to that directory. It will be unavailable when the drive is unmounted; this is intentional.
- Keep text, source scripts, manifests, and guides in this project. Reference external media rather than copying it into Git.
- If MicroBay is unavailable, report the missing mount; do not silently place large files on the internal drive or redownload existing media.
- ARTIFACTS.json inventories external files with size and SHA-256. Run python3 scripts/verify_artifacts.py to check it; use --hash for full content verification.
- Preserve existing evidence. Regeneration scripts can replace derived captures and reports; inspect their output paths before running them.

## Engineering approach

Prefer clear APIs, enforced architectural boundaries, and executable checks for recurring failures. Maintain feature maps that state what users can do, how to reach it, and what observable results establish success. Verify real journeys and durable effects, retain reproducible evidence, and adapt drivers to the platform. Make one implementation-and-verification loop dependable before scaling automation.

Research is not authorization to deploy, merge, install plugins, send messages, or launch autonomous workflows. Do implementation work when requested and follow the user's current scope.
