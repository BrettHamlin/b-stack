import SettingsInterface
import XCTest

final class CheckpointJourneys: XCTestCase {
    // A closing brace in a comment: }
    /* and in a block comment: } */
    let rawSample = #"quote: " }"#
    let interpolated = "state: \(true ? "}" : "{")"

    enum Checkpoint: String {
        case start
    }

    func testReachesSettings() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.switches[NotificationSettingsUIID.toggle].waitForExistence(timeout: 20), Checkpoint.start.rawValue)
    }
}
