@testable import Core
import SettingsInterface
import XCTest

final class TestableIDJourneys: XCTestCase {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find(UIID("notificationSettings.toggle")))
    }
}
