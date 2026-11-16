import Harmonize
import Testing

/// Imports each module may use, including system frameworks. Module-to-module dependencies
/// are declared in Project.swift and checked by `tuist inspect dependencies`.
let allowedImports: [String: Set<String>] = [
    "Core": ["Foundation"],
    "SettingsInterface": ["Foundation", "Core"],
    "SettingsLogic": ["Foundation", "Core", "SettingsInterface", "ComposableArchitecture"],
    "Settings": ["Foundation", "SwiftUI", "Observation", "Core", "SettingsInterface", "SettingsLogic", "ComposableArchitecture"],
    "Platform": ["Foundation", "Core", "SettingsInterface"],
    "Fixtures": ["Foundation", "Core", "SettingsInterface", "Platform"],
    "App": ["Foundation", "SwiftUI", "Settings", "SettingsInterface", "Platform"],
    "AppVerify": ["Foundation", "SwiftUI", "Settings", "SettingsInterface", "Fixtures"],
]

@Test func moduleBoundaries() {
    for (module, allowed) in allowedImports.sorted(by: { $0.key < $1.key }) {
        Harmonize.productionCode().on("Targets/\(module)").imports().assertTrue(
            rule: Rule(
                id: "module-boundaries",
                description: "[module-boundaries] \(module) may only import: \(allowed.sorted().joined(separator: ", "))",
                fixHint: "Move the code to a module allowed to use it, or pass data in through Core or an Interface module. Don't edit this list; stop and report."
            )
        ) { allowed.contains($0.name) }
    }
}
