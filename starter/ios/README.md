# iOS starter repo (plan)

**Status:** Plan only. Nothing built yet. The layout will change as we discuss verification and build the first real app, and each project may differ.

The goal is a repo you copy to start a new iOS app with stages 0–2 of the [playbook](../../playbook/new-project.md) already done, and stage 3 scaffolded.

## Likely layout

```
<App>/
├── AGENTS.md                  from templates/AGENTS.md
├── CODEOWNERS                 from templates/CODEOWNERS
├── boundaries.yaml            allowed graph and imports
├── Project.swift | project.yml   project manifest (Tuist or XcodeGen; to decide)
├── App/                       thin app target: composition root, fixture-mode launch
├── Modules/
│   ├── Package.swift          strict settings (see platforms/ios-swift.md)
│   └── Sources/
│       ├── Domain/            pure logic and types; Foundation only
│       ├── Data/              persistence and network behind Domain protocols
│       ├── Features/          SwiftUI, main-actor by default
│       └── UIID/              shared accessibility identifiers
├── UITests/                   XCUITest-based driver
├── feature-map/               one YAML file per feature
├── tools/checker/             SwiftSyntax layer-2 checker
├── enforcement/               allowlists and baselines
└── .github/workflows/         build + checker as required checks
```

## Build-up order

1. **Compiler layer:** `Modules/Package.swift` with strict settings, and a deliberately broken branch proving each layer-1 rule fires
2. **Checker:** import check against `boundaries.yaml` first (it covers the compiler's gaps), then escape hatches and suppressions
3. **Foundation:** CI workflow, CODEOWNERS, branch protection
4. **Verification:** fixture mode, `UIID`, a minimal driver, one feature-map entry with evidence. After the verification discussion.
5. **Extract:** after the first real app, replace the drafts in `templates/` with what actually worked

## Open decisions

- Tuist vs XcodeGen (vs a hand-maintained project with a settings check)
- SwiftLint as a stopgap, or the SwiftSyntax checker from day one
- Minimum iOS version
- Driver design (see [05 · Verification](../../guide/05-verification.md))
