import Core
import SettingsInterface
import JourneyKit

extension UIID {
    static func invented(_ raw: String) -> UIID {
        self.init(raw)
    }
}

final class FactoryIDJourneys: Journey {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find(UIID.invented("notificationSettings.toggle")))
    }
}
