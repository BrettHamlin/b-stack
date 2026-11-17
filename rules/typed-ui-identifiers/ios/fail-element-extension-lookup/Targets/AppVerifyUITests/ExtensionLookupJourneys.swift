import SettingsInterface
import XCTest

// Only the extension itself is banned here: the body uses no reserved name, so this case isolates that check.
extension XCTest.XCUIElement {
    func nothing() {}
}

final class ExtensionLookupJourneys: XCTestCase {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        screen.find(NotificationSettingsUIID.toggle).nothing()
    }
}
