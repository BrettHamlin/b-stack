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
    // Text match, deliberately broad: in Targets/*UITests, no string literal may be used as a subscript (except
    // launchEnvironment["KEY"]) or as an identifier argument or predicate, including raw strings (#"..."#). That covers app.switches["..."], a query
    // stored in a variable and subscripted later, .matching(identifier: "...") and NSPredicate "identifier == '...'".
    let patterns = [
        #"([\w)\]]+)\s*\[\s*#*""#,
        #"identifier\s*:\s*#*""#,
        #"identifier\s*(==|BEGINSWITH|CONTAINS|LIKE|MATCHES)"#,
    ]
    var hits: [String] = []
    for source in Harmonize.testCode().sources() {
        guard let path = source.filePath?.path, path.range(of: #"/Targets/[^/]+UITests/"#, options: .regularExpression) != nil else { continue }
        let text = source.source
        for pattern in patterns {
            guard let regex = try? NSRegularExpression(pattern: pattern) else { continue }
            for match in regex.matches(in: text, range: NSRange(text.startIndex..., in: text)) {
                let found = (text as NSString).substring(with: match.range)
                if !found.hasPrefix("launchEnvironment") {
                    hits.append("\(source.fileName ?? path): \(found)")
                }
            }
        }
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] String literal element lookups in \(hits). Find elements by a UIID constant.")
}
