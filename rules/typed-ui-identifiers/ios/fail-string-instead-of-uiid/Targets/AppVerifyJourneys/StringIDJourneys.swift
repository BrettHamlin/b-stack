import SettingsInterface
import JourneyKit

final class StringIDJourneys: Journey {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find("notificationSettings.toggle"))
    }
}
