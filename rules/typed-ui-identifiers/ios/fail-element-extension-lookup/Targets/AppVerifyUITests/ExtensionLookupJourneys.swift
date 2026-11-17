import SettingsInterface
import XCTest

extension XCUIElement {
    func lookupRaw(_ id: String) -> XCUIElement {
        descendants(matching: .any)[id]
    }
}

final class ExtensionLookupJourneys: XCTestCase {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        screen.find(NotificationSettingsUIID.toggle).lookupRaw("notificationSettings.toggle").tap()
    }
}
