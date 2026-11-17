import SettingsInterface
import XCTest

final class StringIDJourneys: XCTestCase {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find("notificationSettings.toggle"))
    }
}
