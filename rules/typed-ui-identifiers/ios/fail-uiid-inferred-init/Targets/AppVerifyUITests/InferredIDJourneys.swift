import SettingsInterface
import XCTest

final class InferredIDJourneys: XCTestCase {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find(.init("notificationSettings.toggle")))
    }
}
