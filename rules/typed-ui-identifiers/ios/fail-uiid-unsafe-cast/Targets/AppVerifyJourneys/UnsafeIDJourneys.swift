import Core
import SettingsInterface
import JourneyKit

final class UnsafeIDJourneys: Journey {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find(unsafeBitCast("notificationSettings.toggle", to: UIID.self)))
    }
}
