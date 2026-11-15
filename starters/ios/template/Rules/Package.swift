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
        .testTarget(
            name: "ArchitectureRules",
            dependencies: [
                .product(name: "Harmonize", package: "Harmonize"),
                .product(name: "SwiftSyntax", package: "swift-syntax"),
                .product(name: "SwiftParser", package: "swift-syntax"),
            ]
        ),
    ]
)
