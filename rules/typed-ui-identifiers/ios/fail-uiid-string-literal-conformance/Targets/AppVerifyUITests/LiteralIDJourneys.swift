import Core
import SettingsInterface
import XCTest

extension UIID: @retroactive ExpressibleByStringLiteral {
    public init(stringLiteral value: String) {
        self.init(value)
    }
}

final class LiteralIDJourneys: XCTestCase {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        tapWhenHittable(screen.find("notificationSettings.toggle"))
    }
}
