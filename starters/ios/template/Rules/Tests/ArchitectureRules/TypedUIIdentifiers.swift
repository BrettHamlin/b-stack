import Foundation
import Harmonize
import SwiftParser
import SwiftSyntax
import Testing

@Test func typedUIIdentifiers() {
    // Views set identifiers from UIIDs: the argument (or the value assigned to a UIKit accessibilityIdentifier) must be
    // `.rawValue` of a `<Feature>UIID.<name>` constant (module-qualified too), `.rawValue` reached from a variable,
    // parameter or self (trusted; review), or a ternary between such values. A UIKit assignment may also be nil.
    // A literal, String(...), concatenation or a String variable fails.
    // Parsed with SwiftSyntax: Harmonize 1.3.0 doesn't expose calls inside computed properties such as a SwiftUI body.
    var hits: [String] = []
    for source in Harmonize.productionCode().sources() {
        let tree = Parser.parse(source: source.source)
        let finder = ViewIdentifierFinder(tree, file: source.fileName ?? "?")
        finder.walk(tree)
        hits += finder.hits
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] String literal accessibility identifiers in \(hits). Use a UIID constant: .accessibilityIdentifier(<Feature>UIID.<name>.rawValue).")
}

@Test func uiIdentifiersAreOnlyDeclaredInInterfaces() {
    // Core and the *Interface modules are the only ones that can reach UIID's package initializer. Keep it that way:
    // - Core's UIID initializers are all `package` (none public or open).
    // - In Core and *Interface, an explicit UIID(...) / UIID.init(...) takes a plain string literal, so it never forwards
    //   an arbitrary String. Indirect construction (.init, Self, init references) is review's job (escape hatches).
    // - Nowhere outside Core may UIID be extended or aliased.
    var hits: [String] = []
    for source in Harmonize.productionCode().sources() + Harmonize.testCode().sources() {
        guard let path = source.filePath?.path else { continue }
        let tree = Parser.parse(source: source.source)
        let finder = UIIDDeclarationFinder(
            tree, file: source.fileName ?? path,
            isCore: path.contains("/Targets/Core/"),
            isInterface: path.range(of: #"/Targets/[^/]+Interface/"#, options: .regularExpression) != nil
        )
        finder.walk(tree)
        hits += finder.hits
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] UIID creation opened up at \(hits). Declare identifiers as `static let x = UIID(\"feature.x\")` in the feature's Interface module; never forward a String into a UIID.")
}

private final class ViewIdentifierFinder: SyntaxVisitor {
    private let converter: SourceLocationConverter
    private let file: String
    var hits: [String] = []

    init(_ tree: SourceFileSyntax, file: String) {
        converter = SourceLocationConverter(fileName: file, tree: tree)
        self.file = file
        super.init(viewMode: .sourceAccurate)
    }

    override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
        let token = node.calledExpression.as(MemberAccessExprSyntax.self)?.declName.baseName
            ?? node.calledExpression.as(DeclReferenceExprSyntax.self)?.baseName
        if let token, bare(token) == "accessibilityIdentifier",
           let argument = node.arguments.first(where: { $0.label == nil })?.expression, !isUIIDRawValue(argument) {
            report(node)
        }
        return .visitChildren
    }

    // UIKit: view.accessibilityIdentifier = ... (an unfolded sequence: [target, =, value])
    override func visit(_ node: SequenceExprSyntax) -> SyntaxVisitorContinueKind {
        let elements = Array(node.elements)
        for index in elements.indices.dropFirst().dropLast() where elements[index].is(AssignmentExprSyntax.self) {
            let target = elements[index - 1].as(MemberAccessExprSyntax.self).map { bare($0.declName.baseName) }
                ?? elements[index - 1].as(DeclReferenceExprSyntax.self).map { bare($0.baseName) }   // implicit self
            guard target == "accessibilityIdentifier" else { continue }
            // Everything after `=` is the value: a UIID value, a ternary between two, or nil (clearing it).
            // `x.rawValue + ".typo"` leaves an extra operator in the sequence, so it fails.
            let value = Array(elements[(index + 1)...])
            if value.count == 1, value[0].is(NilLiteralExprSyntax.self) { continue }
            if !isUIIDValue(value) { report(node) }
        }
        return .visitChildren
    }

    private func report(_ node: some SyntaxProtocol) {
        hits.append("\(file):\(node.startLocation(converter: converter).line)")
    }
}

/// `.rawValue` of a UIID: `<Feature>UIID.<name>.rawValue` (also module-qualified, and indexed: `<Feature>UIID.<name>.at(i, j).rawValue`), or `.rawValue` on a value reached
/// from a variable, parameter or `self` (`id.rawValue`, `self.id.rawValue`, `row.id.rawValue`; trusted, review), or a
/// ternary between two such values with any condition. A chain through a type name must pass a `...UIID` type, so a
/// local String enum doesn't pass.
private func isUIIDRawValue(_ expr: ExprSyntax) -> Bool {
    var expr = expr
    while let tuple = expr.as(TupleExprSyntax.self), tuple.elements.count == 1, let only = tuple.elements.first { expr = only.expression }
    if let sequence = expr.as(SequenceExprSyntax.self) { return isUIIDValue(Array(sequence.elements)) }
    guard let raw = expr.as(MemberAccessExprSyntax.self), bare(raw.declName.baseName) == "rawValue", var base = raw.base else { return false }
    var names: [String] = []                                        // the chain before .rawValue, root last
    while true {                                                    // row?.id, row!.id and items[i].id walk through
        if let call = base.as(FunctionCallExprSyntax.self), let at = call.calledExpression.as(MemberAccessExprSyntax.self),
           bare(at.declName.baseName) == "at", let next = at.base {
            base = next                                             // an indexed UIID: <UIID>.at(...) is still that UIID
        } else if let member = base.as(MemberAccessExprSyntax.self), let next = member.base {
            names.append(bare(member.declName.baseName))
            base = next
        } else if let optional = base.as(OptionalChainingExprSyntax.self) {
            base = optional.expression
        } else if let forced = base.as(ForceUnwrapExprSyntax.self) {
            base = forced.expression
        } else if let subscripted = base.as(SubscriptCallExprSyntax.self) {
            base = subscripted.calledExpression
        } else {
            break
        }
    }
    guard let root = base.as(DeclReferenceExprSyntax.self) else { return false }
    let rootName = bare(root.baseName)
    // A chain from a variable, parameter or self is a value, whatever its properties are called (row.ID): trusted.
    guard rootName.first?.isUppercase == true else { return true }
    // A chain from a type name (Module.Type.member) must pass through a <Feature>UIID type before the member, so a
    // String enum's case named `toggleUIID` doesn't count.
    return ([rootName] + names.dropFirst().reversed()).contains { $0.hasSuffix("UIID") }
}

/// An unfolded expression that is a UIID value: one value, a `??` chain of values (`a?.id.rawValue ?? <UIID value>`),
/// or `<any condition> ? <UIID value> : <UIID value>`, where the else side may itself be such an expression
/// (`a ? A : b ? B : C`; `?:` is right-associative, so the first ternary's else side is everything after it).
private func isUIIDValue(_ elements: [ExprSyntax]) -> Bool {
    if let first = elements.firstIndex(where: { $0.is(UnresolvedTernaryExprSyntax.self) }),
       let ternary = elements[first].as(UnresolvedTernaryExprSyntax.self) {
        return first > 0 && isUIIDRawValue(ternary.thenExpression) && isUIIDValue(Array(elements[(first + 1)...]))
    }
    guard elements.count % 2 == 1 else { return false }
    return elements.indices.allSatisfy { index in
        index % 2 == 0 ? isUIIDRawValue(elements[index])
                       : elements[index].as(BinaryOperatorExprSyntax.self)?.operator.text == "??"
    }
}

private final class UIIDDeclarationFinder: SyntaxVisitor {
    private let converter: SourceLocationConverter
    private let file: String
    private let isCore: Bool
    private let isInterface: Bool
    private var inUIID = false
    var hits: [String] = []

    init(_ tree: SourceFileSyntax, file: String, isCore: Bool, isInterface: Bool) {
        converter = SourceLocationConverter(fileName: file, tree: tree)
        self.file = file
        self.isCore = isCore
        self.isInterface = isInterface
        super.init(viewMode: .sourceAccurate)
    }

    override func visit(_ node: StructDeclSyntax) -> SyntaxVisitorContinueKind {
        inUIID = bare(node.name) == "UIID"
        return .visitChildren
    }

    override func visitPost(_ node: StructDeclSyntax) {
        if bare(node.name) == "UIID" { inUIID = false }
    }

    override func visit(_ node: InitializerDeclSyntax) -> SyntaxVisitorContinueKind {
        if isCore, inUIID, !node.modifiers.contains(where: { $0.name.text == "package" }) { report(node) }
        return .visitChildren
    }

    override func visit(_ node: ExtensionDeclSyntax) -> SyntaxVisitorContinueKind {
        let name = node.extendedType.as(IdentifierTypeSyntax.self).map { bare($0.name) }
            ?? node.extendedType.as(MemberTypeSyntax.self).map { bare($0.name) }
        if name == "UIID", !isCore { report(node) }
        return .visitChildren
    }

    override func visit(_ node: TypeAliasDeclSyntax) -> SyntaxVisitorContinueKind {
        let target = node.initializer.value.as(IdentifierTypeSyntax.self).map { bare($0.name) }
            ?? node.initializer.value.as(MemberTypeSyntax.self).map { bare($0.name) }
        if target == "UIID", !isCore { report(node) }
        return .visitChildren
    }

    // In Core and *Interface: an explicit UIID(...) / UIID.init(...) with one unlabeled argument must be a plain string
    // literal. Indirect construction (.init, Self, init references) is review's job; see rule.toml's escape hatches.
    override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
        guard isCore || isInterface else { return .visitChildren }
        let callee = node.calledExpression.trimmedDescription.replacingOccurrences(of: "`", with: "")
        // Explicit construction only: unrelated `Self(x)` / `.init(x)` stay legal, and deliberate indirection
        // (init references, metatypes) is review's job until identifiers become enums (follow-up).
        let constructs = ["UIID", "UIID.init", "Core.UIID", "Core.UIID.init"].contains(callee)
        if constructs, node.arguments.count == 1, let only = node.arguments.first, only.label == nil,
           !isPlainStringLiteral(only.expression) {
            report(node)
        }
        return .visitChildren
    }

    private func report(_ node: some SyntaxProtocol) {
        hits.append("\(file):\(node.startLocation(converter: converter).line): \(node.trimmedDescription.prefix(60))")
    }
}

private func isPlainStringLiteral(_ expr: ExprSyntax) -> Bool {
    guard let literal = expr.as(StringLiteralExprSyntax.self) else { return false }
    return literal.segments.allSatisfy { $0.is(StringSegmentSyntax.self) }
}

/// An identifier's name without backticks: `` `switches` `` and `switches` are the same name.
private func bare(_ token: TokenSyntax) -> String {
    token.identifier?.name ?? token.text.replacingOccurrences(of: "`", with: "")
}


@Test func noDynamicJourneyAccess() {
    // The compiler hides the UI SDK and raw handles. Reflection and Objective-C dispatch can still recover
    // private objects without naming SDK types, so only these dynamic escapes remain a syntax rule.
    var hits: [String] = []
    for source in Harmonize.productionAndTestCode().on("Targets/AppVerifyJourneys").sources() {
        guard let path = source.filePath?.path, path.contains("/Targets/AppVerifyJourneys/") else { continue }
        let tree = Parser.parse(source: source.source)
        let finder = DynamicJourneyAccessFinder()
        finder.walk(tree)
        if finder.found { hits.append(source.fileName ?? path) }
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] Dynamic UI access in journey bodies at \(hits). Use typed JourneyKit helpers; stop and report if a helper is missing.")
}

private final class DynamicJourneyAccessFinder: SyntaxVisitor {
    private let names: Set<String> = [
        "Mirror", "NSClassFromString", "NSSelectorFromString", "Selector", "unsafeBitCast", "unsafeDowncast",
        "perform", "value", "setValue", "valueForKey", "method", "class_getInstanceMethod",
        "class_getClassMethod", "object_getClass", "dlsym",
        "withUnsafeBytes", "withUnsafeMutableBytes", "withUnsafePointer", "withUnsafeMutablePointer",
    ]
    var found = false

    init() { super.init(viewMode: .sourceAccurate) }

    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind {
        if names.contains(bare(node.baseName)) { found = true }
        return .visitChildren
    }

    override func visit(_ node: MemberAccessExprSyntax) -> SyntaxVisitorContinueKind {
        if names.contains(bare(node.declName.baseName)) { found = true }
        return .visitChildren
    }

    override func visit(_ node: KeyPathPropertyComponentSyntax) -> SyntaxVisitorContinueKind {
        if names.contains(bare(node.declName.baseName)) { found = true }
        return .visitChildren
    }

    override func visit(_ node: IdentifierTypeSyntax) -> SyntaxVisitorContinueKind {
        if names.contains(bare(node.name)) { found = true }
        return .visitChildren
    }
}
