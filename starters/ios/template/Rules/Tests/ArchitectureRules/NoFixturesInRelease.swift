import Harmonize
import Testing

/// Test-mode setups live in Fixtures, and only AppVerify (the test-mode app) may import it. If the shipped App could
/// import it, test mode could ship to users. Text match on import lines across all production code, any access level
/// (`private import Fixtures`) and kind (`import struct Fixtures.Fixture`).
@Test func noFixturesInRelease() {
    var hits: [String] = []
    for source in Harmonize.productionCode().sources() {
        guard let path = source.filePath?.path, !path.contains("/Targets/AppVerify/"), !path.contains("/Targets/Fixtures/") else { continue }
        if source.source.range(of: #"(?m)^\s*(@\w+\s+)*((public|package|internal|fileprivate|private)\s+)?import\s+((typealias|struct|class|enum|protocol|let|var|func)\s+)?Fixtures\b"#, options: .regularExpression) != nil {
            hits.append(source.fileName ?? path)
        }
    }
    #expect(hits.isEmpty, "[no-fixtures-in-release] \(hits) import Fixtures. Only AppVerify may; compose real services in App and test setups in AppVerify.")
}
