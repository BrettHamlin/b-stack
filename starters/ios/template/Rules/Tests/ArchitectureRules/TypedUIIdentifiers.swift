import Foundation
import Harmonize
import SwiftParser
import SwiftSyntax
import Testing

@Test func typedUIIdentifiers() {
    // Views set identifiers from UIID constants (.accessibilityIdentifier(<Feature>UIID.x.rawValue)), never a literal.
    // Parsed with SwiftSyntax: Harmonize 1.3.0 doesn't expose calls inside computed properties such as a SwiftUI body.
    var hits: [String] = []
    for source in Harmonize.productionCode().sources() {
        let tree = Parser.parse(source: source.source)
        let finder = LiteralIdentifierFinder(tree, file: source.fileName ?? "?")
        finder.walk(tree)
        hits += finder.hits
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] String literal accessibility identifiers in \(hits). Use a UIID constant.")
}

private final class LiteralIdentifierFinder: SyntaxVisitor {
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
        if let token, bare(token) == "accessibilityIdentifier", node.arguments.contains(where: { isStringLiteral($0.expression) }) {
            hits.append("\(file):\(node.startLocation(converter: converter).line)")
        }
        return .visitChildren
    }
}

@Test func typedUIIdentifiersInJourneys() {
    // Journeys find elements only through JourneyKit's typed find(_ id: UIID), so a string can't be passed where an
    // identifier is expected (a compile error). Outside JourneyKit.swift, journey files may not use XCUITest's lookup
    // API at all. The rule bans it by name, a closed list from XCUIAutomation's XCUIElementTypeQueryProvider.h and
    // XCUIElementQuery.h (Xcode 27.2): every element-type query (.buttons, .switches, ...), .descendants, .children,
    // .matching, .containing, .element, .allElementsBoundByIndex, plus XCUIApplication, XCUIElementQuery, NSPredicate
    // and .identifier, as member accesses, bare references (implicit self inside an extension) or key-path
    // components, and extending XCUIElement / XCUIElementQuery / XCUIApplication / XCUIElementTypeQueryProvider.
    // Those names are reserved in journey files. A dictionary subscript is never confused with a query, because
    // nothing here inspects subscripts. Creating a UIID outside Core and *Interface is a compile error (package init).
    var hits: [String] = []
    for source in Harmonize.testCode().sources() {
        guard let path = source.filePath?.path, path.range(of: #"/Targets/[^/]+UITests/"#, options: .regularExpression) != nil,
              !path.hasSuffix("/JourneyKit.swift") else { continue }
        let tree = Parser.parse(source: source.source)
        let finder = RawLookupFinder(tree, file: source.fileName ?? path)
        finder.walk(tree)
        hits += finder.hits
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] Raw XCUITest lookups in journeys at \(hits). Find elements with JourneyKit's find(_:) and a UIID constant; add a JourneyKit helper if none fits.")
}

/// XCUITest lookup API, by name. Element-type queries are XCUIElementTypeQueryProvider's properties; firstMatch is
/// left out because it looks nothing up (an element's firstMatch is itself).
private let rawLookupNames: Set<String> = [
    "activityIndicators", "alerts", "browsers", "buttons", "cells", "checkBoxes", "collectionViews", "colorWells",
    "comboBoxes", "datePickers", "decrementArrows", "dialogs", "disclosedChildRows", "disclosureTriangles",
    "dockItems", "drawers", "grids", "groups", "handles", "helpTags", "icons", "images", "incrementArrows",
    "keyboards", "keys", "layoutAreas", "layoutItems", "levelIndicators", "links", "maps", "mattes", "menuBarItems",
    "menuBars", "menuButtons", "menuItems", "menus", "navigationBars", "otherElements", "outlineRows", "outlines",
    "pageIndicators", "pickerWheels", "pickers", "popUpButtons", "popovers", "progressIndicators", "radioButtons",
    "radioGroups", "ratingIndicators", "relevanceIndicators", "rulerMarkers", "rulers", "scrollBars", "scrollViews",
    "searchFields", "secureTextFields", "segmentedControls", "sheets", "sliders", "splitGroups", "splitters",
    "staticTexts", "statusBars", "statusItems", "steppers", "switches", "tabBars", "tabGroups", "tableColumns",
    "tableRows", "tables", "tabs", "textFields", "textViews", "timelines", "toggles", "toolbarButtons", "toolbars",
    "touchBars", "valueIndicators", "webViews", "windows",
    "descendants", "children", "matching", "containing", "element", "allElementsBoundByIndex",
    "allElementsBoundByAccessibilityElement", "identifier", "dictionaryRepresentation",
]

/// Types journeys may not extend outside JourneyKit: an extension could wrap the raw API in a new name.
private let rawLookupExtended: Set<String> = ["XCUIElement", "XCUIElementQuery", "XCUIApplication", "XCUIElementTypeQueryProvider"]

/// Types journeys may not name outside JourneyKit.
private let rawLookupTypes: Set<String> = ["XCUIApplication", "XCUIElementQuery", "NSPredicate"]

private final class RawLookupFinder: SyntaxVisitor {
    private let converter: SourceLocationConverter
    private let file: String
    var hits: [String] = []

    init(_ tree: SourceFileSyntax, file: String) {
        converter = SourceLocationConverter(fileName: file, tree: tree)
        self.file = file
        super.init(viewMode: .sourceAccurate)
    }

    override func visit(_ node: MemberAccessExprSyntax) -> SyntaxVisitorContinueKind {
        if rawLookupNames.contains(bare(node.declName.baseName)) { report(node) }
        if bare(node.declName.baseName) == "init", let base = node.base?.as(DeclReferenceExprSyntax.self),
           rawLookupTypes.contains(bare(base.baseName)) { report(node) }
        return .visitChildren
    }

    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind {
        // Bare names too: inside an extension, `descendants(matching:)` needs no `self.`.
        if rawLookupTypes.contains(bare(node.baseName)) || rawLookupNames.contains(bare(node.baseName)) { report(node) }
        return .visitChildren
    }

    override func visit(_ node: ExtensionDeclSyntax) -> SyntaxVisitorContinueKind {
        let extended = node.extendedType.trimmedDescription.replacingOccurrences(of: "`", with: "")
        if rawLookupExtended.contains(extended) { report(node.extendedType) }
        return .visitChildren
    }

    override func visit(_ node: IdentifierTypeSyntax) -> SyntaxVisitorContinueKind {
        if rawLookupTypes.contains(bare(node.name)) { report(node) }
        return .visitChildren
    }

    override func visit(_ node: KeyPathPropertyComponentSyntax) -> SyntaxVisitorContinueKind {
        if rawLookupNames.contains(bare(node.declName.baseName)) { report(node) }
        return .visitChildren
    }

    private func report(_ node: some SyntaxProtocol) {
        hits.append("\(file):\(node.startLocation(converter: converter).line): \(node.trimmedDescription.prefix(60))")
    }
}

/// An identifier's name without backticks: `` `switches` `` and `switches` are the same name.
private func bare(_ token: TokenSyntax) -> String {
    token.identifier?.name ?? token.text.replacingOccurrences(of: "`", with: "")
}

/// A string literal, also in parentheses or cast (`"x" as String`).
private func isStringLiteral(_ expr: ExprSyntax) -> Bool {
    if expr.is(StringLiteralExprSyntax.self) { return true }
    if let tuple = expr.as(TupleExprSyntax.self), tuple.elements.count == 1, let only = tuple.elements.first {
        return isStringLiteral(only.expression)
    }
    if let sequence = expr.as(SequenceExprSyntax.self), let first = sequence.elements.first {
        return isStringLiteral(first) && sequence.elements.dropFirst().first?.is(UnresolvedAsExprSyntax.self) == true
    }
    if let cast = expr.as(AsExprSyntax.self) { return isStringLiteral(cast.expression) }
    return false
}
