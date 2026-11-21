import XCTest

final class CheckpointJourneys: XCTestCase {
    // A closing brace in a comment: }
    /* and in a block comment: } */
    let rawSample = #"quote: " }"#
    let interpolated = "state: \(true ? "}" : "{")"

    enum Checkpoint: String {
        case start
    }

    func testReachesTheFirstScreen() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10), Checkpoint.start.rawValue)
    }
}
