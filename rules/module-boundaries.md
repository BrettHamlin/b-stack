# module-boundaries

**Status:** Draft
**Layer:** 1 + 2

## Problem
Agents import whatever makes the code compile. UI code reaches into persistence, domain logic imports UI frameworks, and process boundaries get crossed (Lauren's example: Electron renderer importing main-process code, causing jank). Once it happens a few times it looks like the convention.

## Layer
Layer 1 as far as possible: separate modules, each declaring only the dependencies it's allowed. Layer 2 for what the compiler misses: indirect imports, system frameworks, and new dependencies added to the build manifest.

## Enforcement
- One module (package, crate, target) per architectural layer, with dependencies declared in the build manifest
- The default access level hides internals; only intended APIs are public
- A committed allowed-graph file ([template](../templates/boundaries.yaml)). A layer-2 check compares the actual dependencies **and the actual import statements** against it, including permitted system frameworks per module.

## Error message
> `Domain` may not import `SwiftUI`. Domain code must stay UI-free. Put UI code in a feature module and pass data in through Domain types. If a dependency seems genuinely necessary, stop and report; don't edit boundaries.yaml.

## Escape hatches
- Adding a dependency to the build manifest → manifest is protected; graph check fails
- Importing a module reachable indirectly → import check against the allowed graph
- Making internals public to cross a boundary → review of public API changes; optionally a public-API diff check
- Re-exporting a module → import check treats re-exports as dependencies

## Origin
Lauren Tan talk (Dune: `electron-main`/`electron-renderer` import bans). Swift testing showed the compiler blocks undeclared sibling imports but **not** indirect imports or system frameworks, hence the layer-2 half.
