import Foundation
import Harmonize
import SwiftParser
import SwiftSyntax
import Testing

@Test func typedUIIdentifiers() {
    // Text match: Harmonize 1.3.0 doesn't expose calls inside computed properties such as a SwiftUI body.
    let files = Harmonize.productionCode().sources()
        .filter { $0.source.contains(".accessibilityIdentifier(\"") }
        .compactMap(\.fileName)
    #expect(files.isEmpty, "[typed-ui-identifiers] String literal accessibility identifiers in \(files). Use a UIID constant.")
}

@Test func typedUIIdentifiersInJourneys() {
    // UI journeys find elements by the same UIID constants the views set, so a renamed identifier fails to compile.
    // Parsed with SwiftSyntax, so comments and strings are real tokens. A string literal (also in parentheses or
    // String("...")) is rejected:
    // - as a subscript, unless what's subscripted is a dictionary: launchEnvironment, userInfo, environment, or a
    //   variable or parameter in scope that is typed, initialised, cast or copied as one. Optional chaining and force
    //   unwraps are seen through. System UI that can't carry our identifiers is allowed: queries under `keyboards`,
    //   and an XCUIApplication(bundleIdentifier: "com.apple.springboard").
    // - as an `identifier:` argument, e.g. .matching(identifier: "...")
    // - compared with `.identifier` (== or !=)
    // - in an NSPredicate that compares identifier: quoted in the format, or as the argument (positional or
    //   argumentArray) for the placeholder after `identifier <op>`, or as a %K "identifier" key's value.
    // Not caught: a literal bound to a local constant first (let id = "..."; app.switches[id]); review.
    var hits: [String] = []
    for source in Harmonize.testCode().sources() {
        guard let path = source.filePath?.path, path.range(of: #"/Targets/[^/]+UITests/"#, options: .regularExpression) != nil else { continue }
        let tree = Parser.parse(source: source.source)
        let finder = LiteralLookupFinder(tree, file: source.fileName ?? path)
        finder.walk(tree)
        hits += finder.hits
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] String literal element lookups in \(hits). Find elements by a UIID constant. (A dictionary is fine: declare or annotate it as one.)")
}

private final class LiteralLookupFinder: SyntaxVisitor {
    enum Kind { case dictionary, systemApp, other }
    private var scopes: [[String: Kind]] = [[:]]
    private let converter: SourceLocationConverter
    private let file: String
    var hits: [String] = []

    init(_ tree: SourceFileSyntax, file: String) {
        converter = SourceLocationConverter(fileName: file, tree: tree)
        self.file = file
        super.init(viewMode: .sourceAccurate)
    }

    // MARK: Scopes

    private func declare(_ name: String, _ kind: Kind) { scopes[scopes.count - 1][name] = kind }

    private func lookup(_ name: String) -> Kind {
        for scope in scopes.reversed() { if let kind = scope[name] { return kind } }
        return .other
    }

    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind {
        scopes.append([:])
        for parameter in node.signature.parameterClause.parameters {
            let name = (parameter.secondName ?? parameter.firstName).text
            declare(name, isDictionaryType(parameter.type) ? .dictionary : .other)
        }
        return .visitChildren
    }
    override func visitPost(_ node: FunctionDeclSyntax) { scopes.removeLast() }
    override func visit(_ node: ClosureExprSyntax) -> SyntaxVisitorContinueKind { scopes.append([:]); return .visitChildren }
    override func visitPost(_ node: ClosureExprSyntax) { scopes.removeLast() }
    override func visit(_ node: CodeBlockSyntax) -> SyntaxVisitorContinueKind { scopes.append([:]); return .visitChildren }
    override func visitPost(_ node: CodeBlockSyntax) { scopes.removeLast() }

    override func visit(_ node: VariableDeclSyntax) -> SyntaxVisitorContinueKind {
        for binding in node.bindings {
            guard let name = binding.pattern.as(IdentifierPatternSyntax.self)?.identifier.text else { continue }
            var kind = Kind.other
            if let type = binding.typeAnnotation?.type, isDictionaryType(type) { kind = .dictionary }
            if let value = binding.initializer?.value {
                if isDictionary(value) { kind = .dictionary } else if isSpringboard(value) { kind = .systemApp }
            }
            declare(name, kind)
        }
        return .visitChildren
    }

    // MARK: Lookups

    override func visit(_ node: SubscriptCallExprSyntax) -> SyntaxVisitorContinueKind {
        if node.arguments.contains(where: { isLiteral($0.expression) }),
           !isDictionary(node.calledExpression), !isSystemUI(node.calledExpression) {
            report(node)
        }
        return .visitChildren
    }

    override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
        if node.arguments.contains(where: { $0.label?.text == "identifier" && isLiteral($0.expression) }) {
            report(node)
        }
        if let name = node.calledExpression.as(DeclReferenceExprSyntax.self)?.baseName.text, name == "NSPredicate" {
            checkPredicate(node)
        }
        return .visitChildren
    }

    override func visit(_ node: SequenceExprSyntax) -> SyntaxVisitorContinueKind {
        // Unfolded binary expressions: [lhs, operator, rhs, ...]
        let elements = Array(node.elements)
        for (index, element) in elements.enumerated() where index > 0 && index + 1 < elements.count {
            guard let op = element.as(BinaryOperatorExprSyntax.self)?.operator.text, op == "==" || op == "!=" else { continue }
            let lhs = elements[index - 1], rhs = elements[index + 1]
            if (isIdentifierMember(lhs) && isLiteral(rhs)) || (isIdentifierMember(rhs) && isLiteral(lhs)) { report(node) }
        }
        return .visitChildren
    }

    private func checkPredicate(_ node: FunctionCallExprSyntax) {
        let arguments = Array(node.arguments)
        guard let formatArgument = arguments.first, formatArgument.label?.text == "format",
              let format = literalText(formatArgument.expression) else { return }
        if format.range(of: #"identifier\s*(==|!=|BEGINSWITH|CONTAINS|LIKE|MATCHES)\s*['"]"#, options: [.regularExpression, .caseInsensitive]) != nil {
            report(node)
            return
        }
        var values: [ExprSyntax] = arguments.dropFirst().map(\.expression)
        if let array = arguments.first(where: { $0.label?.text == "argumentArray" })?.expression.as(ArrayExprSyntax.self) {
            values = array.elements.map(\.expression)
        }
        // Placeholders in order; flag the value for one that follows `identifier <op>`, or follows a %K whose key is "identifier".
        let placeholder = try? NSRegularExpression(pattern: #"%(@|K|l?[dif])"#)
        let ns = format as NSString
        let matches = placeholder?.matches(in: format, range: NSRange(location: 0, length: ns.length)) ?? []
        for (index, match) in matches.enumerated() where index < values.count {
            let before = ns.substring(to: match.range.location)
            let comparesIdentifier = before.range(of: #"identifier\s*(==|!=|BEGINSWITH|CONTAINS|LIKE|MATCHES)\s*$"#, options: [.regularExpression, .caseInsensitive]) != nil
            let keyIsIdentifier = index > 0 && ns.substring(with: matches[index - 1].range) == "%K"
                && literalText(values[index - 1]) == "identifier"
            if (comparesIdentifier || keyIsIdentifier) && isLiteral(values[index]) { report(node) }
        }
    }

    // MARK: Classification

    private func unwrapped(_ expr: ExprSyntax) -> ExprSyntax {
        if let e = expr.as(OptionalChainingExprSyntax.self) { return unwrapped(e.expression) }
        if let e = expr.as(ForceUnwrapExprSyntax.self) { return unwrapped(e.expression) }
        if let e = expr.as(TupleExprSyntax.self), e.elements.count == 1, let only = e.elements.first { return unwrapped(only.expression) }
        if let e = expr.as(TryExprSyntax.self) { return unwrapped(e.expression) }
        if let e = expr.as(AwaitExprSyntax.self) { return unwrapped(e.expression) }
        return expr
    }

    private func literalText(_ expr: ExprSyntax) -> String? {
        let expr = unwrapped(expr)
        if let literal = expr.as(StringLiteralExprSyntax.self) {
            return literal.segments.map { $0.as(StringSegmentSyntax.self)?.content.text ?? "" }.joined()
        }
        if let call = expr.as(FunctionCallExprSyntax.self),
           call.calledExpression.as(DeclReferenceExprSyntax.self)?.baseName.text == "String",
           call.arguments.count == 1, let only = call.arguments.first {
            return literalText(only.expression)
        }
        return nil
    }

    private func isLiteral(_ expr: ExprSyntax) -> Bool { literalText(expr) != nil }

    private func isIdentifierMember(_ expr: ExprSyntax) -> Bool {
        unwrapped(expr).as(MemberAccessExprSyntax.self)?.declName.baseName.text == "identifier"
    }

    private func isDictionaryType(_ type: TypeSyntax) -> Bool {
        if type.is(DictionaryTypeSyntax.self) { return true }
        if let optional = type.as(OptionalTypeSyntax.self) { return isDictionaryType(optional.wrappedType) }
        if let iuo = type.as(ImplicitlyUnwrappedOptionalTypeSyntax.self) { return isDictionaryType(iuo.wrappedType) }
        return type.as(IdentifierTypeSyntax.self)?.name.text == "Dictionary"
    }

    private func isDictionary(_ expr: ExprSyntax) -> Bool {
        let expr = unwrapped(expr)
        if expr.is(DictionaryExprSyntax.self) { return true }
        if let cast = expr.as(AsExprSyntax.self) { return isDictionaryType(cast.type) }
        if let sequence = expr.as(SequenceExprSyntax.self) {
            // `x as! [K: V]` and `x as? Dictionary<K, V>` are unfolded into [x, as, type].
            let elements = Array(sequence.elements)
            if let last = elements.last?.as(TypeExprSyntax.self), elements.dropLast().last?.is(UnresolvedAsExprSyntax.self) == true {
                return isDictionaryType(last.type)
            }
            return false
        }
        if let call = expr.as(FunctionCallExprSyntax.self) {
            let callee = unwrapped(call.calledExpression)
            if callee.is(DictionaryExprSyntax.self) { return true }                       // [K: V]()
            if let generic = callee.as(GenericSpecializationExprSyntax.self),
               generic.expression.as(DeclReferenceExprSyntax.self)?.baseName.text == "Dictionary" { return true }
            return false
        }
        if let member = expr.as(MemberAccessExprSyntax.self) {
            return ["launchEnvironment", "userInfo", "environment"].contains(member.declName.baseName.text)
        }
        if let reference = expr.as(DeclReferenceExprSyntax.self) {
            return lookup(reference.baseName.text) == .dictionary
        }
        return false
    }

    private func isSpringboard(_ expr: ExprSyntax) -> Bool {
        guard let call = unwrapped(expr).as(FunctionCallExprSyntax.self),
              call.calledExpression.as(DeclReferenceExprSyntax.self)?.baseName.text == "XCUIApplication" else { return false }
        return call.arguments.contains { $0.label?.text == "bundleIdentifier" && literalText($0.expression) == "com.apple.springboard" }
    }

    /// System UI that can't carry our identifiers: the keyboard, and the springboard (permission alerts).
    private func isSystemUI(_ expr: ExprSyntax) -> Bool {
        var current: ExprSyntax? = unwrapped(expr)
        while let node = current {
            if let member = node.as(MemberAccessExprSyntax.self) {
                if member.declName.baseName.text == "keyboards" { return true }
                current = member.base.map(unwrapped)
            } else if let call = node.as(FunctionCallExprSyntax.self) {
                if isSpringboard(ExprSyntax(call)) { return true }
                current = unwrapped(call.calledExpression)
            } else if let sub = node.as(SubscriptCallExprSyntax.self) {
                current = unwrapped(sub.calledExpression)
            } else if let reference = node.as(DeclReferenceExprSyntax.self) {
                return lookup(reference.baseName.text) == .systemApp
            } else {
                return false
            }
        }
        return false
    }

    private func report(_ node: some SyntaxProtocol) {
        let line = node.startLocation(converter: converter).line
        hits.append("\(file):\(line): \(node.trimmedDescription.prefix(80))")
    }
}
