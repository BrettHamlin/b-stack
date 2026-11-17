import SettingsInterface
import JourneyKit

final class RawConstantJourneys: Journey {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches[NotificationSettingsUIID.toggle.rawValue].tap()
    }
}
