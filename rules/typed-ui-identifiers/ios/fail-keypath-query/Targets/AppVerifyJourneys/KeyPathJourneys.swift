import SettingsInterface
import JourneyKit

final class KeyPathJourneys: Journey {
    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        let path = \XCUIElement.switches
        screen.find(NotificationSettingsUIID.toggle)[keyPath: path].firstMatch.tap()
    }
}
