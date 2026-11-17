import Foundation
import Harmonize
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
    // Text match on Targets/*UITests with comments removed. A string literal (plain or raw #"..."#) is rejected:
    // - as the subscript of an element query: app.switches["..."], .descendants(matching: .any)["..."], or a
    //   variable holding a query (let toggles = app.switches; toggles["..."])
    // - as an identifier argument: .matching(identifier: "...")
    // - compared with an identifier: element.identifier == "..." or NSPredicate(format: "identifier == '...'")
    // Ordinary dictionaries (launchEnvironment["KEY"], userInfo["k"]) and typed predicates
    // (NSPredicate(format: "identifier == %@", NotificationSettingsUIID.toggle)) are fine.
    // Not caught: a literal bound to a local constant first (let id = "..."; app.switches[id]).
    let queries = "buttons|switches|toggles|staticTexts|cells|otherElements|textFields|secureTextFields|textViews|images|"
        + "links|navigationBars|tables|collectionViews|scrollViews|alerts|sheets|sliders|pickers|pickerWheels|"
        + "segmentedControls|tabBars|toolbars|searchFields|menuItems|keys|webViews|windows|steppers|"
        + "activityIndicators|progressIndicators"
    var hits: [String] = []
    for source in Harmonize.testCode().sources() {
        guard let path = source.filePath?.path, path.range(of: #"/Targets/[^/]+UITests/"#, options: .regularExpression) != nil else { continue }
        let text = withoutComments(source.source)
        // Variables that hold an element query: assigned from app, an XCUIApplication or another query.
        let assigned = matches(#"\b(?:let|var)\s+(\w+)\s*=\s*[^\n]*\b(?:app|XCUIApplication\(\))\."#, in: text).map { $0[1] }
        let held = assigned.isEmpty ? "" : "|" + assigned.joined(separator: "|")
        let patterns = [
            #"\b(?:"# + queries + held + #")\s*\[\s*#*""#,
            #"\b(?:descendants|children)\(matching:[^)]*\)\s*\[\s*#*""#,
            #"identifier\s*:\s*#*""#,
            #"identifier\s*(?:==|!=|BEGINSWITH|CONTAINS|LIKE|MATCHES)\s*(?:#*"|')"#,
        ]
        for pattern in patterns {
            for found in matches(pattern, in: text) {
                hits.append("\(source.fileName ?? path): \(found[0])")
            }
        }
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] String literal element lookups in \(hits). Find elements by a UIID constant.")
}

private func withoutComments(_ text: String) -> String {
    text.replacingOccurrences(of: #"(?s)/\*.*?\*/"#, with: " ", options: .regularExpression)
        .replacingOccurrences(of: #"//[^\n]*"#, with: "", options: .regularExpression)
}

private func matches(_ pattern: String, in text: String) -> [[String]] {
    guard let regex = try? NSRegularExpression(pattern: pattern) else { return [] }
    let ns = text as NSString
    return regex.matches(in: text, range: NSRange(location: 0, length: ns.length)).map { match in
        (0..<match.numberOfRanges).map { match.range(at: $0).location == NSNotFound ? "" : ns.substring(with: match.range(at: $0)) }
    }
}
