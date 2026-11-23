import ModuleShape
import SwiftSyntax
import Testing

/// Network, disk, preferences (including SwiftUI's @AppStorage), keychain, process and environment APIs. Only Platform (the real services) and Fixtures
/// (test mode's fakes) may use them. Everything else reaches the outside world through an Interface protocol that
/// Platform implements, so logic stays testable and the screens never bypass it.
private let ioNames: Set<String> = [
    "FileManager", "FileHandle", "FileWrapper", "NSFileCoordinator", "InputStream", "OutputStream", "fopen",
    "URLSession", "URLSessionConfiguration", "NSURLConnection", "NWConnection", "NWListener",
    "UserDefaults", "NSUbiquitousKeyValueStore", "AppStorage",
    "SecItemAdd", "SecItemCopyMatching", "SecItemUpdate", "SecItemDelete",
    "Process", "ProcessInfo",
]
/// Types whose `init(contentsOf…:)` reads a file or URL: Data(contentsOf:), String(contentsOfFile:), ...
private let readingTypes: Set<String> = [
    "Data", "String", "NSData", "NSString", "NSArray", "NSDictionary", "NSAttributedString", "AttributedString",
]
/// Modules that do no I/O. Platform and Fixtures do it; tests and journeys aren't shipped.
private let ioFreeRoles: Set<Role> = [.core, .interface, .logic, .view, .app, .appVerify]

@Test func noIOOutsidePlatform() {
    var inLogic: [String] = []
    var elsewhere: [String] = []
    for module in declared where ioFreeRoles.contains(module.role) {
        for source in moduleSources(module.name) {
            let finder = IOFinder(source)
            finder.walk(source.tree)
            if module.role == .logic { inLogic += finder.hits } else { elsewhere += finder.hits }
        }
    }
    #expect(inLogic.isEmpty, "[no-io-in-logic] I/O in a Logic module: \(inLogic.joined(separator: ", ")). Define a client protocol in the feature's Interface module, implement it in Platform, inject it into the reducer and call it from an effect.")
    #expect(elsewhere.isEmpty, "[io-only-in-platform] I/O outside Platform: \(elsewhere.joined(separator: ", ")). Only Platform (and test mode's Fixtures) talks to the network, disk, preferences, keychain or environment. Define a client protocol in the feature's Interface module, implement it in Platform, and let the feature's Logic call it.")
}

/// Finds I/O API names (as names, not text: comments, strings and `append(contentsOf:)` don't count), file-reading
/// initializers and `write(to:)` / `write(toFile:)` calls.
private final class IOFinder: SyntaxVisitor {
    private let source: ModuleSource
    private(set) var hits: [String] = []

    init(_ source: ModuleSource) {
        self.source = source
        super.init(viewMode: .sourceAccurate)
    }

    private func hit(_ node: some SyntaxProtocol, _ what: String) {
        let entry = "\(source.location(node)) \(what)"
        if !hits.contains(entry) { hits.append(entry) }
    }

    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind {
        let name = plainName(node.baseName)
        if ioNames.contains(name) { hit(node, name) }
        return .visitChildren
    }

    override func visit(_ node: IdentifierTypeSyntax) -> SyntaxVisitorContinueKind {
        let name = plainName(node.name)
        if ioNames.contains(name) { hit(node, name) }
        return .visitChildren
    }

    override func visit(_ node: MemberTypeSyntax) -> SyntaxVisitorContinueKind {
        let name = plainName(node.name)
        if ioNames.contains(name) { hit(node, name) }
        return .visitChildren
    }

    override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
        let label = node.arguments.first?.label.map(plainName) ?? ""
        var type: String?
        if let reference = node.calledExpression.as(DeclReferenceExprSyntax.self) {
            type = plainName(reference.baseName)
        } else if let member = node.calledExpression.as(MemberAccessExprSyntax.self) {
            let method = plainName(member.declName.baseName)
            if method == "init" {
                // Data.init(contentsOf:), Foundation.Data.init(contentsOf:)
                type = member.base?.as(DeclReferenceExprSyntax.self).map { plainName($0.baseName) }
                    ?? member.base?.as(MemberAccessExprSyntax.self).map { plainName($0.declName.baseName) }
            } else if readingTypes.contains(method) {
                type = method  // Foundation.Data(contentsOf:)
            } else if method == "write", ["to", "toFile", "toURL"].contains(label) {
                hit(node, "write(\(label):)")
            }
        }
        if let type, readingTypes.contains(type), label.hasPrefix("contentsOf") {
            hit(node, "\(type)(\(label):)")
        }
        return .visitChildren
    }
}
