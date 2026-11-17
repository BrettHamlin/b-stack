import SettingsInterface
import XCTest

/// The test is declared only on the base class, so ProfileJourneys runs it as ProfileJourneys/testEditsName.
class JourneyBase: XCTestCase {
    func testEditsName() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.switches[NotificationSettingsUIID.toggle].waitForExistence(timeout: 20))
    }
}

final class ProfileJourneys: JourneyBase, @unchecked Sendable {}
