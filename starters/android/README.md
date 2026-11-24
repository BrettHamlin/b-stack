# Android starter

A Kotlin Android app: Jetpack Compose screens over feature logic written as Kotlin Multiplatform common code, Gradle modules whose role comes from their folder, and journeys that drive the running app on an emulator. Copied into a new repo by the [new-project skill](../../skills/new-project/SKILL.md). Only what's listed as built exists.

## What's built

| Piece | Path | Status |
|---|---|---|
| Gradle build: every module's settings from its role, through build-logic's convention plugins; modules have no build files, only a `module.toml` naming the modules they use (`uses`); each gets its role's libraries | `template/settings.gradle.kts`, `template/build-logic/`, `template/arch/shape.json` | ✅ A new module in a role's folder is built and checked without editing a protected file; a link or library outside the role fails the build |
| Module shape: core, a feature's api, logic and ui, platform, fixtures, the shipped app and the test-mode app, journeykit, journeys and the runner | `template/arch/shape.json` | ✅ |
| Example feature: a tally of named items (record, show, a failed save keeps the old tally, a bad name is refused), with Turbine tests of every state and a property test | `template/features/tally/`, `template/platform/files/`, `template/app/`, `template/app-verify/` | ✅ |
| Property test for the example feature: 200 seeded random sequences of names and adds, checked state by state against a model of the spec | `template/features/tally/logic/src/commonTest/kotlin/tally/logic/TallyPropertyTest.kt` | ✅ Under a second. No library: a seeded `Random` |
| Gate command: compiler, detekt, lint, konsist, arch, deps, settings, tests, verify, release | `template/scripts/check.py` | ✅ Every gate passes in about 2.5 min with a warm Gradle daemon and a running emulator (2026-11-24, Mac mini) |
| detekt with type resolution, plus our own rule set (no `as` casts, no `throw`, no `.` call or `for` loop on a Java result of unknown nullability) | `template/arch/detekt.yml`, `template/arch/detekt-rules/` | ✅ |
| Android Lint's NewApi (a call above minSdk 29 without a version check) as the lint gate, an error with no baseline | `template/build-logic/`, `template/scripts/check.py` | ✅ |
| Architecture tests (Konsist, the Kotlin tool Harmonize is modeled on): imports by role, singletons and service locators, ad-hoc scopes and threads, typed UI identifiers, I/O only in platform modules, views that hold no clients, a thin shipped app, exhaustive tests, no skipped tests | `template/arch/konsist/` | ✅ |
| Arch checks: module folders and source sets against the shape, no build files or Java in modules, no suppressions or opt-ins (a text match nothing in a file can switch off) | `template/scripts/arch.py` | ✅ |
| Dependency checks: libraries only from Google's and Maven Central's repositories, every artifact's SHA-256 in Gradle's verification metadata, licenses from each POM (permissive for what ships), and the shipped app's merged manifest (its own and every library's) against the owner's list of permissions and exported components | `template/scripts/deps.py`, `template/gradle/verification-metadata.xml`, `template/arch/manifest.toml` | ✅ |
| Settings gate: the enforcement settings in effect (Gradle's dependency verification, build cache and init scripts; per module, every Kotlin compilation's options, the Android SDK levels and Lint options, the app's release shrinking, detekt's and the test tasks' failure handling) against `arch/settings.json`, and CODEOWNERS covering every enforcement path; build-logic's `bstackSettings` task reports them after everything that configures them has run | `template/scripts/settings.py`, `template/build-logic/src/main/kotlin/bstack/Settings.kt`, `template/arch/settings.json` | ✅ `settings.py record` writes the file from what's in effect, for the owner |
| Typed UI identifiers: `UiId` made only in a feature's api module (its constructor's opt-in is granted there alone), elements tagged with `Modifier.uiId`, list and grid items as `id.at(row, column)`, journeys finding them through a `Screen` that takes only `UiId`s | `template/core/`, `template/core-ui/`, `template/verify/journeykit/` | ✅ A string or a `UiId` made elsewhere doesn't compile |
| Verification: feature map (each feature with a journey that turns the device and one that has its process end in the background), journeys as common code (no UiAutomator, Android or JVM on their classpath), a self-instrumenting runner that drives app-verify through UiAutomator, generated adapters, screenshots as evidence; then a smoke launch of the shipped app on a fresh install | `template/scripts/verify.py`, `template/verify/`, `template/feature-map/` | ✅ Seven tally journeys (relaunch, failed save, bad name, saved data at start, rotation, process death, unreadable file) and the smoke launch, about 70 s on the Mac mini |
| Journeys against the release build (the release gate): every journey runs again against app-verify built with the shipped app's release settings (R8 shrinking and obfuscation), and the shipped app's release build is launched; code that only breaks after R8 fails here | `template/scripts/verify.py` (`release`), `template/build-logic/src/main/kotlin/bstack/ModulePlugin.kt` | ✅ All seven tally journeys pass against the R8 build; a class name shown on screen passes in debug and fails here (it became `v01`) |
| Test mode as a separate app (`app-verify`, its own application id per checkout) composed with `fixtures`, which the shipped app can't use; StrictMode there kills the app on disk writes or network on the main thread, so a journey fails | `template/app-verify/`, `template/fixtures/` | ✅ |
| Composition roots: each app's `Application` class builds process-wide services once (not per Activity, which rotation recreates); the Activity only shows each feature's entry point with a model built from them (`rememberModel` in core-ui keeps it across rotation, and gives it a `Saved` for what must survive process death). Views get only their model, never a client; the shipped app only composes | `template/app/src/main/kotlin/app/StarterApp.kt`, `template/app-verify/src/main/kotlin/appverify/VerifyApp.kt` | ✅ |
| Emulator: one AVD from the pinned system image, booted headless when needed, with a machine-wide lock so checkouts take turns; hand use through `emulator.py run` | `template/scripts/emulator.py` | ✅ |
| Pinned tools, checksum-verified, no global install: the JDK, Gradle, Android's command-line tools, and the SDK packages at pinned revisions (tools.py stops if Google has published a newer one), per machine: Apple silicon Macs and x64 Linux | `template/tools.toml`, `template/scripts/tools.py` | ✅ Temurin JDK 21.0.13.1, Gradle 9.9.2, cmdline-tools 23.0, platform 37.2, build-tools 36.0.0, emulator 37.3.10, the API 37 image (arm64 on a Mac, x86_64 on Linux) |
| JDK, SDK, emulator images, Gradle's own folder and all build output in a configurable cache folder | `template/scripts/paths.py`, `template/scripts/tools.py` | ✅ `.build/` becomes a link into it; stops if the folder is missing |
| Check record, observe mode: check.py records the git tree each run saw; `audit` says whether a commit's tree was checked; each Claude Code hand-back is logged; each commit gets a `Checked:` trailer. Never blocks | `template/scripts/handback.py`, `template/.claude/settings.json`, `template/.githooks/` | ✅ The iOS starter's, with this starter's gates |
| New-feature command: a feature's api, logic and ui modules (a `<Feature>Ui`, a model with `Saved`, an entry point), its feature-map entry, a journey stub that turns the device and has the process end, the adapters, and the links from `verify/journeys`, `app` and `app-verify`; everything passes compiler, detekt, Lint, Konsist, arch, deps and settings as created, and its test and journey fail until written | `template/scripts/new_feature.py` | ✅ A created feature, shown in both apps with a real Turbine test and journey, passed every gate (2026-11-24) |
| Release builds: an app bundle for Play and an APK, shrunk and obfuscated by R8, signed with the upload key from `BSTACK_UPLOAD_*` (or a throwaway test key, named `-test-signed`), signatures checked, and the release APK installed with no data and launched on the emulator; the R8 mapping is kept per version | `template/scripts/package.py`, `template/build-logic/src/main/kotlin/bstack/ModulePlugin.kt` | ✅ The release build of the tally app starts and stays up (2026-11-24) |
| CI: every gate and the release build on a Linux runner (the emulator gets KVM there), signed with the upload key on `main` from repository secrets; release outputs and evidence uploaded | `template/.github/workflows/check.yml` | ✅ Make `check` a required status check; b-stack's own CI runs the same commands on the starter |
| Verify skill for agents: the gate, exploring through `emulator.py run`, adding a feature | `template/.agents/skills/verify/` (linked from `.claude/skills`) | ✅ |
| Agent instructions, CODEOWNERS | `template/AGENTS.template.md`, `template/CODEOWNERS` | ✅ Draft; placeholders to fill in |

Pins (2026-11-23, the latest stable of each unless noted): Kotlin 2.4.21, Android Gradle Plugin 9.5.2, Gradle 9.9.2, compileSdk 37.2, targetSdk 37, minSdk 29, kotlinx-coroutines 1.11.0, Compose UI 1.13.0, Material 3 1.5.0, activity-compose 1.13.0, lifecycle-viewmodel-compose 2.11.1, Turbine 1.2.1, Konsist 0.18.1, detekt 2.0.0-alpha.6 (detekt's only line that runs on Kotlin 2.4 with type resolution), UiAutomator 2.4.1. The JDK, command-line tools and system image are pinned for Apple silicon Macs and for x64 Linux (CI).

## Module shape

| Module folder | Role | Kind | May use |
|---|---|---|---|
| `core` | core: shared types, `UiId` | common | nothing |
| `core-ui` | core-ui: `Modifier.uiId` and shared Compose pieces | Android library | core |
| `features/<name>/api` | api: the feature's types, client interfaces and `<Feature>Ui` identifiers | common | core |
| `features/<name>/logic` | logic: the feature's model (`StateFlow` state, `send(action)`), effects through injected clients | common | core, its own api |
| `features/<name>/ui` | ui: Compose screens that render state and send actions, and the feature's entry point | Android library | core, core-ui, its own api and logic |
| `platform/<name>` | platform: real I/O, implementing feature clients | Android library | core, feature apis |
| `fixtures` | fixtures: test-mode setups | Android library | core, feature apis, platform |
| `app` | the shipped app (a composition root) | Android application | everything but fixtures and the verify modules |
| `app-verify` | the test-mode app (a composition root) | Android application | the same, plus fixtures |
| `verify/journeykit` | the `Journey`, `Screen` and `Element` journeys see | common | core |
| `verify/journeys` | journey bodies | common | journeykit, core, feature apis |
| `verify/runner` | the UiAutomator driver and generated adapters (code-owned) | Android test app for app-verify | journeykit, journeys, core |

"Common" modules are Kotlin Multiplatform modules with a JVM and a JS target, compiled as common code, so the JDK and Android don't exist there. This table is `template/arch/shape.json` (protected), with each role's libraries, which every module of the role gets, so they all resolve the versions `gradle/verification-metadata.xml` lists. `settings.gradle.kts` includes every folder of a role, and build-logic applies the role's settings; a module's `module.toml` names the modules it uses, checked against the shape when the build is configured.

## Strict settings (build-logic)

| Setting | Effect |
|---|---|
| `allWarningsAsErrors`, `progressiveMode` on every Kotlin compilation | Warnings block the build, including a redundant `else`, a deprecated platform API, a delicate coroutines API and an error suppression |
| Opt-ins per role (`opt_in`, `test_opt_in` in arch/shape.json) | Code can't opt in itself; tests get `ExperimentalCoroutinesApi` for virtual time |
| A JS target beside the JVM target on common modules, and `compileCommonMainKotlinMetadata` in the compiler gate | Logic can't name `java.*`, `Thread`, `System` or `android.*` |
| The `DeclaresUiId` opt-in only on api modules | A `UiId` made anywhere else doesn't compile |
| `implementation` links only, from module.toml; libraries by role | A module sees only the modules it declares; it can't add a library |
| `FAIL_ON_PROJECT_REPOS`, Google and Maven Central only; verification metadata | No other source of libraries; every artifact checked against its SHA-256 |
| `android.builder.sdkDownload=false` | SDK packages come only from tools.toml's pins |
| The shipped app's release build: R8 minification and resource shrinking, signed only with the upload key | The release APK, built with the same code and settings as the bundle, is launched on the emulator before anything is called done; an unsigned release fails package.py |

## Not built yet (in order)

1. **Publishing to Play:** `package.py` builds and signs the app bundle; uploading it (a Play Console track, Play App Signing) is done by hand.
