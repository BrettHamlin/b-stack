// swift-tools-version: 6.2
import PackageDescription

let strict: [SwiftSetting] = [
    .enableUpcomingFeature("InternalImportsByDefault"),
    .enableUpcomingFeature("MemberImportVisibility"),
    .enableUpcomingFeature("ExistentialAny"),
    .treatAllWarnings(as: .error),
]

let package = Package(
    name: "Modules",
    platforms: [.iOS(.v18), .macOS(.v15)],
    targets: [
        .target(name: "Domain", swiftSettings: strict),
        .target(name: "Data", dependencies: ["Domain"], swiftSettings: strict),
        .target(
            name: "Features",
            dependencies: ["Domain"],
            swiftSettings: strict + [.defaultIsolation(MainActor.self)]
        ),
    ],
    swiftLanguageModes: [.v6]
)
