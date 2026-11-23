import ModuleShape
import SwiftSyntax
import Testing

/// The shipped App only puts screens together and plugs the real services in. No journey ever runs it (they run
/// AppVerify), so anything it decides or does is never verified. Behaviour belongs in a feature's Logic.
@Test func thinApp() {
    var hits: [String] = []
    for module in declared where module.role == .app {
        for source in moduleSources(module.name) {
            let finder = AppBehaviourFinder(source)
            finder.walk(source.tree)
            hits += finder.hits
        }
    }
    #expect(hits.isEmpty, "[thin-app] Behaviour in App: \(hits.joined(separator: ", ")). App only composes: a `@main` struct whose `body` puts the screens in a WindowGroup, stored properties that build each feature's store from its Logic with Platform's services, and View structs that compose screens. Move decisions and side effects into a feature's Logic, where tests and journeys run them.")
}

/// SwiftUI modifiers that run code when something happens.
private let eventModifiers: Set<String> = [
    "task", "onAppear", "onDisappear", "onChange", "onReceive", "onOpenURL", "onContinueUserActivity",
    "backgroundTask", "onSubmit", "onTapGesture", "refreshable",
]

private final class AppBehaviourFinder: SyntaxVisitor {
    private let source: ModuleSource
    private(set) var hits: [String] = []

    init(_ source: ModuleSource) {
        self.source = source
        super.init(viewMode: .sourceAccurate)
    }

    private func hit(_ node: some SyntaxProtocol, _ what: String) -> SyntaxVisitorContinueKind {
        hits.append("\(source.location(node)) \(what)")
        return .visitChildren
    }

    // Declarations: App has structs with properties and nothing else.
    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "func \(node.name.text)") }
    override func visit(_ node: InitializerDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "init") }
    override func visit(_ node: DeinitializerDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "deinit") }
    override func visit(_ node: SubscriptDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "subscript") }
    override func visit(_ node: ExtensionDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "extension") }
    override func visit(_ node: ClassDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "class \(node.name.text)") }
    override func visit(_ node: ActorDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "actor \(node.name.text)") }
    override func visit(_ node: EnumDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "enum \(node.name.text)") }
    override func visit(_ node: ProtocolDeclSyntax) -> SyntaxVisitorContinueKind { hit(node, "protocol \(node.name.text)") }
    override func visit(_ node: VariableDeclSyntax) -> SyntaxVisitorContinueKind {
        // A file-level declaration sits in a CodeBlockItem, in the file's item list.
        node.parent?.parent?.parent?.is(SourceFileSyntax.self) == true ? hit(node, "global variable") : .visitChildren
    }

    // Decisions and loops.
    override func visit(_ node: IfExprSyntax) -> SyntaxVisitorContinueKind { hit(node, "if") }
    override func visit(_ node: GuardStmtSyntax) -> SyntaxVisitorContinueKind { hit(node, "guard") }
    override func visit(_ node: SwitchExprSyntax) -> SyntaxVisitorContinueKind { hit(node, "switch") }
    override func visit(_ node: UnresolvedTernaryExprSyntax) -> SyntaxVisitorContinueKind { hit(node, "?: (ternary)") }
    override func visit(_ node: TernaryExprSyntax) -> SyntaxVisitorContinueKind { hit(node, "?: (ternary)") }
    override func visit(_ node: ForStmtSyntax) -> SyntaxVisitorContinueKind { hit(node, "for") }
    override func visit(_ node: WhileStmtSyntax) -> SyntaxVisitorContinueKind { hit(node, "while") }
    override func visit(_ node: RepeatStmtSyntax) -> SyntaxVisitorContinueKind { hit(node, "repeat") }
    override func visit(_ node: DoStmtSyntax) -> SyntaxVisitorContinueKind { hit(node, "do") }
    override func visit(_ node: DeferStmtSyntax) -> SyntaxVisitorContinueKind { hit(node, "defer") }

    // Work started from App: tasks and event handlers.
    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind {
        plainName(node.baseName) == "Task" ? hit(node, "Task") : .visitChildren
    }
    override func visit(_ node: MemberAccessExprSyntax) -> SyntaxVisitorContinueKind {
        let name = plainName(node.declName.baseName)
        return eventModifiers.contains(name) ? hit(node, ".\(name)") : .visitChildren
    }
}
