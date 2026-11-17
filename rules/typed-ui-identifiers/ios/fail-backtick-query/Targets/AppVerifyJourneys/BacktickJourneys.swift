import SettingsInterface
import JourneyKit

final class BacktickJourneys: Journey {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        screen.find(NotificationSettingsUIID.toggle).`switches`["notificationSettings.toggle"].tap()
    }
}
