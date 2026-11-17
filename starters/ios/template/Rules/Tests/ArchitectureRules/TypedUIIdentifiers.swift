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
    // Journeys find elements only through JourneyKit's typed find(_ id: UIID), so a string can't be passed where an
    // identifier is expected (a compile error). Outside JourneyKit.swift, journey files may not use XCUITest's lookup
    // API at all. The rule bans it by name, a closed list from XCUIAutomation's XCUIElementTypeQueryProvider.h and
    // XCUIElementQuery.h (Xcode 27.2): every element-type query (.buttons, .switches, ...), .descendants, .children,
    // .matching, .containing, .element, .allElementsBoundByIndex, plus XCUIApplication, XCUIElementQuery, NSPredicate
    // and .identifier, as member accesses or key-path components. A dictionary subscript is never confused with a
    // query, because nothing here inspects subscripts.
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

@Test func uiIdentifiersComeFromInterfaces() {
    // Only *Interface modules create UIIDs, so views and journeys share one set of constants and nobody invents one
    // from a string elsewhere. Core declares the type; every other UIID(...) call outside Targets/*Interface fails.
    var hits: [String] = []
    for source in Harmonize.productionCode().sources() + Harmonize.testCode().sources() {
        guard let path = source.filePath?.path, path.range(of: #"/Targets/[^/]+Interface/"#, options: .regularExpression) == nil else { continue }
        let tree = Parser.parse(source: source.source)
        let finder = UIIDConstructionFinder(tree, file: source.fileName ?? path)
        finder.walk(tree)
        hits += finder.hits
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] UIIDs created outside an Interface module at \(hits). Add the constant to the feature's <Feature>UIID enum in its Interface module.")
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
    "allElementsBoundByAccessibilityElement", "identifier",
]

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
        if rawLookupNames.contains(node.declName.baseName.text) { report(node) }
        if node.declName.baseName.text == "init", let base = node.base?.as(DeclReferenceExprSyntax.self),
           rawLookupTypes.contains(base.baseName.text) { report(node) }
        return .visitChildren
    }

    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind {
        if rawLookupTypes.contains(node.baseName.text) { report(node) }
        return .visitChildren
    }

    override func visit(_ node: IdentifierTypeSyntax) -> SyntaxVisitorContinueKind {
        if rawLookupTypes.contains(node.name.text) { report(node) }
        return .visitChildren
    }

    override func visit(_ node: KeyPathPropertyComponentSyntax) -> SyntaxVisitorContinueKind {
        if rawLookupNames.contains(node.declName.baseName.text) { report(node) }
        return .visitChildren
    }

    private func report(_ node: some SyntaxProtocol) {
        hits.append("\(file):\(node.startLocation(converter: converter).line): \(node.trimmedDescription.prefix(60))")
    }
}

private final class UIIDConstructionFinder: SyntaxVisitor {
    private let converter: SourceLocationConverter
    private let file: String
    var hits: [String] = []

    init(_ tree: SourceFileSyntax, file: String) {
        converter = SourceLocationConverter(fileName: file, tree: tree)
        self.file = file
        super.init(viewMode: .sourceAccurate)
    }

    override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
        let callee = node.calledExpression.trimmedDescription
        if ["UIID", "UIID.init", "Core.UIID", "Core.UIID.init"].contains(callee) {
            hits.append("\(file):\(node.startLocation(converter: converter).line): \(node.trimmedDescription.prefix(60))")
        }
        return .visitChildren
    }
}
