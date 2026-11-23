import ModuleShape
import SwiftSyntax
import Testing

/// A feature's view gets only its store. Clients (the protocols declared in Interface and Logic modules, which
/// Platform and Fixtures implement) go into the reducer, built by the feature's Logic and passed in by App and
/// AppVerify. A view that can name a client could hold one and call it, going around the reducer and its tests; a
/// public initializer that takes anything besides a store could be handed a client's work as a closure.
@Test func viewsHoldNoClients() {
    var clients: Set<String> = []
    for module in declared where module.role == .interface || module.role == .logic {
        for source in moduleSources(module.name) {
            let finder = ProtocolFinder(viewMode: .sourceAccurate)
            finder.walk(source.tree)
            clients.formUnion(finder.names)
        }
    }
    var hits: [String] = []
    for module in declared where module.role == .view {
        for source in moduleSources(module.name) {
            let finder = ClientNameFinder(source, clients: clients)
            finder.walk(source.tree)
            hits += finder.hits
        }
    }
    #expect(hits.isEmpty, "[views-hold-no-clients] A view names a client or takes more than its store: \(hits.joined(separator: ", ")). A view takes only its store (`init(store: StoreOf<Feature>)`). Build the store in the feature's Logic with a function that takes the clients, like `NotificationSettings.store(preferences:)`, and let App and AppVerify pass it in. The view sends actions; the reducer calls the clients.")
}

private final class ProtocolFinder: SyntaxVisitor {
    private(set) var names: Set<String> = []

    override func visit(_ node: ProtocolDeclSyntax) -> SyntaxVisitorContinueKind {
        names.insert(plainName(node.name))
        return .skipChildren
    }
}

private final class ClientNameFinder: SyntaxVisitor {
    private let source: ModuleSource
    private let clients: Set<String>
    private(set) var hits: [String] = []

    init(_ source: ModuleSource, clients: Set<String>) {
        self.source = source
        self.clients = clients
        super.init(viewMode: .sourceAccurate)
    }

    private func check(_ node: some SyntaxProtocol, _ token: TokenSyntax) -> SyntaxVisitorContinueKind {
        let name = plainName(token)
        if clients.contains(name) { hits.append("\(source.location(node)) \(name)") }
        return .visitChildren
    }

    override func visit(_ node: InitializerDeclSyntax) -> SyntaxVisitorContinueKind {
        let exposed = node.modifiers.contains { ["public", "open", "package"].contains($0.name.text) }
        for parameter in node.signature.parameterClause.parameters where exposed {
            let type = parameter.type.trimmedDescription.replacingOccurrences(of: "ComposableArchitecture.", with: "")
            if !(type.hasPrefix("StoreOf<") || type.hasPrefix("Store<")) {
                hits.append("\(source.location(parameter)) public init takes `\(parameter.firstName.text): \(type)`")
            }
        }
        return .visitChildren
    }

    override func visit(_ node: IdentifierTypeSyntax) -> SyntaxVisitorContinueKind { check(node, node.name) }
    override func visit(_ node: MemberTypeSyntax) -> SyntaxVisitorContinueKind { check(node, node.name) }
    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind { check(node, node.baseName) }
}
