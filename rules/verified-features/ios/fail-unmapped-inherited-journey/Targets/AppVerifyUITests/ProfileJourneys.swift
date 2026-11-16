import SettingsInterface
import XCTest

class JourneyBase: XCTestCase {
    func launchApp() -> XCUIApplication {
        let app = XCUIApplication()
        app.launch()
        return app
    }
}

final class ProfileJourneys: JourneyBase, @unchecked Sendable {
    func testEditsName() {
        let app = launchApp()
        XCTAssertTrue(app.switches[NotificationSettingsUIID.toggle].waitForExistence(timeout: 20))
    }
}
