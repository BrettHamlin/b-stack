import ProjectDescription

let strict: SettingsDictionary = [
    "SWIFT_VERSION": "6.0",
    "SWIFT_TREAT_WARNINGS_AS_ERRORS": "YES",
    "GCC_TREAT_WARNINGS_AS_ERRORS": "YES",
    "OTHER_SWIFT_FLAGS": "$(inherited) -enable-upcoming-feature InternalImportsByDefault -enable-upcoming-feature MemberImportVisibility -enable-upcoming-feature ExistentialAny",
]
let mainActorByDefault: SettingsDictionary = ["SWIFT_DEFAULT_ACTOR_ISOLATION": "MainActor"]

func module(_ name: String, dependencies: [String] = [], ui: Bool = false) -> Target {
    .target(
        name: name,
        destinations: .iOS,
        product: .framework,
        bundleId: "dev.bstack.starter.\(name.lowercased())",
        deploymentTargets: .iOS("18.0"),
        sources: ["Targets/\(name)/**"],
        dependencies: dependencies.map { .target(name: $0) },
        settings: .settings(base: ui ? strict.merging(mainActorByDefault) { $1 } : strict)
    )
}

let project = Project(
    name: "Starter",
    targets: [
        module("Core"),
        module("SettingsInterface", dependencies: ["Core"]),
        module("Settings", dependencies: ["SettingsInterface", "Core"], ui: true),
        module("Platform", dependencies: ["Core"]),
        .target(
            name: "App",
            destinations: .iOS,
            product: .app,
            bundleId: "dev.bstack.starter",
            deploymentTargets: .iOS("18.0"),
            infoPlist: .default,
            sources: ["Targets/App/**"],
            dependencies: [.target(name: "Settings"), .target(name: "SettingsInterface"), .target(name: "Platform")],
            settings: .settings(base: strict.merging(mainActorByDefault) { $1 })
        ),
    ]
)
