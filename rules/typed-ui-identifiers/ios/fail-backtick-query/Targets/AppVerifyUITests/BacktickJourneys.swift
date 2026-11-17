import SettingsInterface
import XCTest

final class BacktickJourneys: XCTestCase {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        screen.find(NotificationSettingsUIID.toggle).`switches`["notificationSettings.toggle"].tap()
    }
}
