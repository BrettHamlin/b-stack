import Harmonize
import Testing

@Test func typedUIIdentifiers() {
    // Text match: Harmonize 1.3.0 doesn't expose calls inside computed properties such as a SwiftUI body.
    let files = Harmonize.productionCode().sources()
        .filter { $0.source.contains(".accessibilityIdentifier(\"") }
        .compactMap(\.fileName)
    #expect(files.isEmpty, "[typed-ui-identifiers] String literal accessibility identifiers in \(files). Use a UIID constant.")
}
