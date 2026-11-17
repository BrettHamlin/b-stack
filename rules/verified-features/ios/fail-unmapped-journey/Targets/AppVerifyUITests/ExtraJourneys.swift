import SettingsInterface
import XCTest

final class ExtraJourneys: XCTestCase {
    func testOpensSettings() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        XCTAssertTrue(screen.find(NotificationSettingsUIID.toggle).exists)
    }
}
