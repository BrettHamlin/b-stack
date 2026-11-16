import SettingsInterface
import XCTest

final class ExtraJourneys: XCTestCase {
    func testOpensSettings() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.switches[NotificationSettingsUIID.toggle].waitForExistence(timeout: 20))
    }
}
