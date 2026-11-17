import SettingsInterface
import JourneyKit

final class InferredIDJourneys: Journey {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find(.init("notificationSettings.toggle")))
    }
}
