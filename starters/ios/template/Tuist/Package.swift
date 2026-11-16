// swift-tools-version: 6.0
import PackageDescription

#if TUIST
import ProjectDescription

/// TCA and the libraries it uses are linked as shared frameworks. Static linking (Tuist's default) puts a separate
/// copy into every module that uses them, which splits TCA's dependency system between copies.
let packageSettings = PackageSettings(
    productTypes: [
        "ComposableArchitecture": .framework,
        "CasePaths": .framework,
        "CasePathsCore": .framework,
        // Used only while compiling macros, which can't link shared frameworks.
        "CasePathsMacrosSupport": .staticFramework,
        "Clocks": .framework,
        "CombineSchedulers": .framework,
        "ConcurrencyExtras": .framework,
        "CustomDump": .framework,
        "Dependencies": .framework,
        "IdentifiedCollections": .framework,
        "IssueReporting": .framework,
        "OrderedCollections": .framework,
        "Perception": .framework,
        "PerceptionCore": .framework,
        "Sharing": .framework,
        "SwiftNavigation": .framework,
        "SwiftUINavigation": .framework,
        "UIKitNavigation": .framework,
    ]
)
#endif

let package = Package(
    name: "Dependencies",
    dependencies: [
        .package(url: "https://github.com/pointfreeco/swift-composable-architecture", exact: "1.26.2"),
    ]
)
