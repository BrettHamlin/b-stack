import Harmonize
import Testing

/// TCA's TestStore fails a test that leaves any state change, received action or running effect unasserted.
/// These calls switch that off.
private let relaxers = ["exhaustivity = .off", ".skipReceivedActions(", ".skipInFlightEffects("]

@Test func exhaustiveTests() {
    var hits: [String] = []
    for source in Harmonize.testCode().sources() {
        for relaxer in relaxers where source.source.contains(relaxer) {
            hits.append("\(source.fileName ?? "?"): \(relaxer)")
        }
    }
    #expect(hits.isEmpty, "[exhaustive-tests] Non-exhaustive TestStore in \(hits). Assert every state change and received action.")
}
