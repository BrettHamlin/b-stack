// The module shape: which modules the project has and which may depend on which. Project.swift builds its targets
// from this and Features.swift; Rules/Tests/ArchitectureRules/ModuleBoundaries.swift checks the code and the generated
// project against it (it compiles this file too, through a link in Rules/Sources/ModuleShape). Changing the shape
// needs the owner. Agents add features, and the optional links below, in Features.swift.

/// A feature: `<Name>Interface`, `<Name>Logic`, `<Name>` (the view) and `<Name>Tests`, plus the links it uses.
public struct Feature: Sendable {
    public let name: String
    public let links: Set<FeatureLink>

    public init(_ name: String, links: Set<FeatureLink> = []) {
        self.name = name
        self.links = links
    }
}

/// Links a feature may add, each inside the shape. The links that every feature has are always there.
public enum FeatureLink: String, Sendable, CaseIterable {
    case logicUsesCore  // <Feature>Logic → Core
    case viewUsesCore  // <Feature> → Core
    case testsUseCore  // <Feature>Tests → Core
    case platformImplementsInterface  // Platform → <Feature>Interface: Platform implements the feature's clients
    case fixturesUseInterface  // Fixtures → <Feature>Interface
    case appUsesInterface  // App → <Feature>Interface
    case appVerifyUsesInterface  // AppVerify → <Feature>Interface
}

/// Links between the shared modules an app may add.
public enum SharedLink: String, Sendable, CaseIterable {
    case platformUsesCore  // Platform → Core
    case fixturesUseCore  // Fixtures → Core
    case fixturesUsePlatform  // Fixtures → Platform
    case appUsesPlatform  // App → Platform
}

public enum Role: String, Sendable {
    case core, interface, logic, view, tests, platform, fixtures, app, appVerify, journeyKit, journeys, uiTests
}

public struct Module: Sendable, Equatable {
    public let name: String
    public let role: Role
    /// Project modules it depends on.
    public let dependencies: [String]
    /// Packages it depends on.
    public let external: [String]
    /// System frameworks it may import; nil for test targets, whose imports Rules doesn't check.
    public let systemImports: Set<String>?
}

public let composableArchitecture = "ComposableArchitecture"

/// Every module, with the dependencies the shape gives it for these features and shared links.
public func modules(_ features: [Feature], shared: Set<SharedLink>) -> [Module] {
    func module(_ name: String, _ role: Role, _ dependencies: [String], external: [String] = [], imports: Set<String>?) -> Module {
        Module(name: name, role: role, dependencies: dependencies, external: external, systemImports: imports)
    }
    func interfaces(_ link: FeatureLink) -> [String] {
        features.filter { $0.links.contains(link) }.map { "\($0.name)Interface" }
    }
    func core(_ on: Bool) -> [String] { on ? ["Core"] : [] }

    var all = [module("Core", .core, [], imports: ["Foundation"])]
    for feature in features {
        let name = feature.name
        all += [
            module("\(name)Interface", .interface, ["Core"], imports: ["Foundation"]),
            module("\(name)Logic", .logic, ["\(name)Interface"] + core(feature.links.contains(.logicUsesCore)),
                   external: [composableArchitecture], imports: ["Foundation"]),
            module(name, .view, ["\(name)Logic", "\(name)Interface"] + core(feature.links.contains(.viewUsesCore)),
                   external: [composableArchitecture], imports: ["Foundation", "SwiftUI", "Observation"]),
            module("\(name)Tests", .tests, ["\(name)Logic", "\(name)Interface"] + core(feature.links.contains(.testsUseCore)),
                   external: [composableArchitecture], imports: nil),
        ]
    }
    let views = features.map(\.name)
    // Each app builds every feature's store from its Logic and hands it to the view, so views never hold a client.
    let logics = features.map { "\($0.name)Logic" }
    all += [
        module("Platform", .platform, interfaces(.platformImplementsInterface) + core(shared.contains(.platformUsesCore)),
               imports: ["Foundation"]),
        // Test-mode setups. Only AppVerify links this (no-fixtures-in-release).
        module("Fixtures", .fixtures, (shared.contains(.fixturesUsePlatform) ? ["Platform"] : [])
               + interfaces(.fixturesUseInterface) + core(shared.contains(.fixturesUseCore)), imports: ["Foundation"]),
        // The shipped app's composition root.
        module("App", .app, views + logics + interfaces(.appUsesInterface) + (shared.contains(.appUsesPlatform) ? ["Platform"] : []),
               imports: ["Foundation", "SwiftUI"]),
        // The app in test mode, driven by scripts/verify.py. Never shipped.
        module("AppVerify", .appVerify, views + logics + interfaces(.appVerifyUsesInterface) + ["Fixtures"],
               imports: ["Foundation", "SwiftUI"]),
        module("JourneyKit", .journeyKit, ["Core"], imports: ["XCTest"]),
        module("AppVerifyJourneys", .journeys, ["JourneyKit"] + features.map { "\($0.name)Interface" }, imports: ["Foundation"]),
        module("AppVerifyUITests", .uiTests, ["AppVerify", "AppVerifyJourneys"], imports: nil),
    ]
    return all
}

/// The whole shape: every module with every optional link on. A link not in here needs the owner.
public func fullShape(_ features: [Feature]) -> [Module] {
    modules(features.map { Feature($0.name, links: Set(FeatureLink.allCases)) }, shared: Set(SharedLink.allCases))
}
