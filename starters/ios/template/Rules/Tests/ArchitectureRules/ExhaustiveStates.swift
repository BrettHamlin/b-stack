import Harmonize
import SwiftParser
import SwiftSyntax
import Testing

/// A switch whose cases are all enum-case patterns (`.draft`, `.failed(let e)`) must not have
/// a `default:`: it hides newly added cases from the compiler.
private final class CatchAllFinder: SyntaxVisitor {
    var lines: [Int] = []
    let converter: SourceLocationConverter

    init(_ tree: SourceFileSyntax, file: String) {
        converter = SourceLocationConverter(fileName: file, tree: tree)
        super.init(viewMode: .sourceAccurate)
    }

    override func visit(_ node: SwitchExprSyntax) -> SyntaxVisitorContinueKind {
        let clauses = node.cases.compactMap { $0.as(SwitchCaseSyntax.self) }
        let defaults = clauses.filter { $0.label.is(SwitchDefaultLabelSyntax.self) }
        let patterns = clauses.compactMap { $0.label.as(SwitchCaseLabelSyntax.self) }.flatMap(\.caseItems).map(\.pattern)
        let allEnumCases = !patterns.isEmpty && patterns.allSatisfy { pattern in
            let text = pattern.trimmedDescription
            return text.hasPrefix(".") || text.hasPrefix("let .") || text.hasPrefix("var .")
        }
        if allEnumCases, let first = defaults.first {
            lines.append(first.startLocation(converter: converter).line)
        }
        return .visitChildren
    }
}

@Test func exhaustiveStates() {
    var hits: [String] = []
    for source in Harmonize.productionCode().sources() {
        let tree = Parser.parse(source: source.source)
        let finder = CatchAllFinder(tree, file: source.fileName ?? "?")
        finder.walk(tree)
        hits += finder.lines.map { "\(source.fileName ?? "?"):\($0)" }
    }
    #expect(hits.isEmpty, "[exhaustive-states] Catch-all default in an enum switch at \(hits). Handle every case explicitly.")
}
