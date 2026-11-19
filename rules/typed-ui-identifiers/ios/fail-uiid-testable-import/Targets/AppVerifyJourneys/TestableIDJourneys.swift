@testable import Core
import SettingsInterface
import JourneyKit

final class TestableIDJourneys: Journey {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find(UIID("notificationSettings.toggle")))
    }
}
