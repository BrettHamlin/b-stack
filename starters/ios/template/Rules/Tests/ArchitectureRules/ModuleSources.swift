import Foundation
import SwiftParser
import SwiftSyntax

/// A parsed Swift file and its path from the project root, for rules that read code with SwiftSyntax.
struct ModuleSource {
    let file: String
    let tree: SourceFileSyntax

    /// "<file>:<line>" for a node in this file.
    func location(_ node: some SyntaxProtocol) -> String {
        "\(file):\(node.startLocation(converter: SourceLocationConverter(fileName: file, tree: tree)).line)"
    }
}

/// Every Swift file under Targets/<module>/, subfolders included. Harmonize's productionCode() skips folders named
/// *Tests or *Fixtures; this skips nothing, so the rules using it see every file the module compiles.
func moduleSources(_ module: String) -> [ModuleSource] {
    let folder = projectRoot.appendingPathComponent("Targets/\(module)")
    guard let walker = FileManager.default.enumerator(at: folder, includingPropertiesForKeys: nil) else { return [] }
    var sources: [ModuleSource] = []
    for case let url as URL in walker where url.pathExtension == "swift" {
        guard let text = try? String(contentsOf: url, encoding: .utf8) else { continue }
        let components = url.standardizedFileURL.pathComponents
        let start = components.lastIndex(of: "Targets") ?? 0
        sources.append(ModuleSource(file: components[start...].joined(separator: "/"), tree: Parser.parse(source: text)))
    }
    return sources.sorted { $0.file < $1.file }
}

/// A name as written, without backticks.
func plainName(_ token: TokenSyntax) -> String {
    token.text.trimmingCharacters(in: CharacterSet(charactersIn: "`"))
}
