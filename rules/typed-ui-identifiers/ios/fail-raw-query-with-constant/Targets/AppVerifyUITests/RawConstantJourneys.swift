import SettingsInterface
import XCTest

final class RawConstantJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches[NotificationSettingsUIID.toggle.rawValue].tap()
    }
}
