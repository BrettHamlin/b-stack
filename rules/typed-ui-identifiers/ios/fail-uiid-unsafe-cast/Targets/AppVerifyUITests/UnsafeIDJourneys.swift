import Core
import SettingsInterface
import XCTest

final class UnsafeIDJourneys: XCTestCase {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find(unsafeBitCast("notificationSettings.toggle", to: UIID.self)))
    }
}
