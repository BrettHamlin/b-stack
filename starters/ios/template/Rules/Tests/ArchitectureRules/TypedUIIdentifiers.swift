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
    // Text match on Targets/*UITests with comments removed (nested ones too; string contents are kept). Deny by
    // default: a string literal (plain or raw #"..."#) is rejected
    // - as any subscript, unless what's subscripted is a known dictionary: launchEnvironment, userInfo, or a variable
    //   typed as a dictionary, initialised with a dictionary literal, or copied from one of those. So
    //   app.switches["..."], app.datePickers["..."], let q: XCUIElementQuery = ...; q["..."] and helper()["..."] all fail.
    // - as an identifier argument: .matching(identifier: "...")
    // - compared with an identifier: element.identifier == "...", NSPredicate(format: "identifier == '...'") or
    //   NSPredicate(format: "identifier == %@", "...")
    // Not caught: a literal bound to a local constant first (let id = "..."; app.switches[id]).
    var hits: [String] = []
    for source in Harmonize.testCode().sources() {
        guard let path = source.filePath?.path, path.range(of: #"/Targets/[^/]+UITests/"#, options: .regularExpression) != nil else { continue }
        let text = withoutComments(source.source)
        // Keywords can precede an array or dictionary literal (return ["a": 1]); they aren't subscripts.
        var dictionaries: Set<String> = ["launchEnvironment", "userInfo", "return", "in", "case", "throw", "await", "try", "yield", "else"]
        let declarations = [
            #"\b(?:let|var)\s+(\w+)\s*:\s*\[[^\]\n]*:[^\]\n]*\]"#,
            #"\b(?:let|var)\s+(\w+)\s*(?::[^=\n]*)?=\s*\[\s*(?:#*"[^"\n]*"\s*:|:)"#,
            #"\b(?:let|var)\s+(\w+)\s*=\s*[\w.()]*\.(?:launchEnvironment|userInfo|environment)\b"#,
        ]
        for pattern in declarations {
            for found in matches(pattern, in: text) { dictionaries.insert(found[1]) }
        }
        for found in matches(#"(\w+|\))\s*\[\s*#*""#, in: text) where !dictionaries.contains(found[1]) {
            hits.append("\(source.fileName ?? path): \(found[0])")
        }
        let patterns = [
            #"identifier\s*:\s*#*""#,
            #"identifier\s*(?:==|!=|BEGINSWITH|CONTAINS|LIKE|MATCHES)\s*(?:#*"|')"#,
            // A format string that compares identifier, given a literal argument: NSPredicate(format: "identifier == %@", "...")
            ##"format:\s*#*"[^"\n]*identifier[^"\n]*"#*\s*,\s*#*""##,
        ]
        for pattern in patterns {
            for found in matches(pattern, in: text) {
                hits.append("\(source.fileName ?? path): \(found[0])")
            }
        }
    }
    #expect(hits.isEmpty, "[typed-ui-identifiers] String literal element lookups in \(hits). Find elements by a UIID constant.")
}

/// Swift source with comments replaced by a space. Handles // and nested /* */ comments, and leaves string literals
/// ("...", """...""", #"..."#) intact, so a // inside a string is kept.
private func withoutComments(_ text: String) -> String {
    let c = Array(text)
    var out: [Character] = []
    var i = 0
    func starts(_ s: String, at k: Int) -> Bool {
        let p = Array(s)
        return k + p.count <= c.count && Array(c[k..<(k + p.count)]) == p
    }
    while i < c.count {
        if starts("//", at: i) {
            while i < c.count && c[i] != "\n" { i += 1 }
            out.append(" ")
        } else if starts("/*", at: i) {
            var depth = 0
            repeat {
                if starts("/*", at: i) { depth += 1; i += 2 } else if starts("*/", at: i) { depth -= 1; i += 2 } else { i += 1 }
            } while depth > 0 && i < c.count
            out.append(" ")
        } else if c[i] == "#" || c[i] == "\"" {
            var j = i
            while j < c.count && c[j] == "#" { j += 1 }
            let hashes = j - i
            guard j < c.count && c[j] == "\"" else { out.append(c[i]); i += 1; continue }
            let quote = starts("\"\"\"", at: j) ? "\"\"\"" : "\""
            let closing = quote + String(repeating: "#", count: hashes)
            let escape = "\\" + String(repeating: "#", count: hashes)
            j += quote.count
            while j < c.count && !starts(closing, at: j) {
                j += starts(escape, at: j) ? escape.count + 1 : 1
            }
            j = min(c.count, j + closing.count)
            out.append(contentsOf: c[i..<j])
            i = j
        } else {
            out.append(c[i])
            i += 1
        }
    }
    return String(out)
}

private func matches(_ pattern: String, in text: String) -> [[String]] {
    guard let regex = try? NSRegularExpression(pattern: pattern) else { return [] }
    let ns = text as NSString
    return regex.matches(in: text, range: NSRange(location: 0, length: ns.length)).map { match in
        (0..<match.numberOfRanges).map { match.range(at: $0).location == NSNotFound ? "" : ns.substring(with: match.range(at: $0)) }
    }
}
