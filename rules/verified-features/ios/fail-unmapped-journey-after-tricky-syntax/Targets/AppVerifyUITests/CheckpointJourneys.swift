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
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        XCTAssertTrue(screen.find(NotificationSettingsUIID.toggle).exists, Checkpoint.start.rawValue)
    }
}
