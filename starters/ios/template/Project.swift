import ProjectDescription
import ProjectDescriptionHelpers

let strict: SettingsDictionary = [
    "SWIFT_VERSION": "6.0",
    "SWIFT_TREAT_WARNINGS_AS_ERRORS": "YES",
    "GCC_TREAT_WARNINGS_AS_ERRORS": "YES",
    "OTHER_SWIFT_FLAGS": "$(inherited) -enable-upcoming-feature InternalImportsByDefault -enable-upcoming-feature MemberImportVisibility -enable-upcoming-feature ExistentialAny",
]
let mainActorByDefault: SettingsDictionary = ["SWIFT_DEFAULT_ACTOR_ISOLATION": "MainActor"]
/// Core and the *Interface modules share a Swift package name, so `package` declarations (UIID's initializer) are
/// visible to them and to nothing else: only an Interface module can create a UIID. Testability is off for them, so
/// `@testable import` can't reach that initializer either (nothing tests these modules through @testable).
let identifierPackage: SettingsDictionary = ["SWIFT_PACKAGE_NAME": "StarterIdentifiers", "ENABLE_TESTABILITY": "NO"]

let journeyKitFlags = "$(inherited) -enable-upcoming-feature InternalImportsByDefault -enable-upcoming-feature MemberImportVisibility -enable-upcoming-feature ExistentialAny -enable-library-evolution"

/// Targets come from the module shape and Features.swift (Tuist/ProjectDescriptionHelpers). Add features and links
/// there, not here: ModuleBoundaries.swift fails if this project's targets or dependencies differ from the shape's.
func target(_ module: Module) -> Target {
    let product: Product
    var bundleId = "dev.bstack.starter.\(module.name.lowercased())"
    var sources: SourceFilesList = ["Targets/\(module.name)/**"]
    var settings = strict
    switch module.role {
    case .core, .interface:
        product = .framework
        settings = strict.merging(identifierPackage) { $1 }
    case .logic, .platform, .fixtures:
        product = .framework
    case .view:
        product = .framework
        settings = strict.merging(mainActorByDefault) { $1 }
    case .tests:
        product = .unitTests
    case .app, .appVerify:
        product = .app
        bundleId = module.role == .app ? "dev.bstack.starter" : "dev.bstack.starter.verify"
        settings = strict.merging(mainActorByDefault) { $1 }
    case .journeyKit:
        // Resilience keeps the internal XCTest import out of journey clients. Only this module sees the UI SDK.
        product = .framework
        settings = strict.merging(["ENABLE_TESTING_SEARCH_PATHS": "YES", "OTHER_SWIFT_FLAGS": .string(journeyKitFlags)]) { $1 }
    case .journeys:
        // Bodies have no testing framework paths: importing XCTest or XCUIAutomation is a compiler error.
        product = .framework
        settings = strict.merging(["ENABLE_TESTING_SEARCH_PATHS": "NO"]) { $1 }
    case .uiTests:
        // Generated XCTestCase adapters; scripts/verify.py checks them against the body source.
        product = .uiTests
        bundleId = "dev.bstack.starter.verifyuitests"
        sources = ["Targets/AppVerifyUITests/GeneratedJourneys.swift"]
    }
    return .target(
        name: module.name,
        destinations: .iOS,
        product: product,
        bundleId: bundleId,
        deploymentTargets: .iOS("18.0"),
        infoPlist: .default,
        sources: sources,
        dependencies: module.dependencies.map { .target(name: $0) } + module.external.map { .external(name: $0) },
        settings: .settings(base: settings)
    )
}

// Core is not resilient: a resilient Core would make its enums non-frozen, so every switch over one would need
// `@unknown default` and adding a state would no longer break unhandled sites (exhaustive-states).
let targets: [Target] = modules(features, shared: sharedLinks).map(target)

/// Every unit-test target, so the tests gate (scheme UnitTests) runs a new feature's tests without anyone listing them.
let unitTests: [TargetReference] = targets.filter { $0.product == .unitTests }.map { .target($0.name) }

let project = Project(
    name: "Starter",
    targets: targets,
    schemes: [
        .scheme(
            name: "UnitTests",
            buildAction: .buildAction(targets: unitTests),
            testAction: .targets(unitTests.map { .testableTarget(target: $0) })
        ),
        .scheme(
            name: "AppVerify",
            buildAction: .buildAction(targets: ["AppVerify", "AppVerifyUITests"]),
            testAction: .targets(["AppVerifyUITests"]),
            runAction: .runAction(executable: "AppVerify")
        ),
    ]
)
