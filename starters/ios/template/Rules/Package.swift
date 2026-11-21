// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Rules",
    platforms: [.macOS(.v15)],
    dependencies: [
        .package(url: "https://github.com/perrystreetsoftware/Harmonize.git", exact: "1.3.0"),
        .package(url: "https://github.com/swiftlang/swift-syntax.git", from: "601.0.1"),
    ],
    targets: [
        // Links to Tuist/ProjectDescriptionHelpers/{ModuleShape,Features}.swift: the shape Project.swift builds from.
        .target(name: "ModuleShape"),
        .testTarget(
            name: "ArchitectureRules",
            dependencies: [
                "ModuleShape",
                .product(name: "Harmonize", package: "Harmonize"),
                .product(name: "SwiftSyntax", package: "swift-syntax"),
                .product(name: "SwiftParser", package: "swift-syntax"),
            ]
        ),
    ]
)
