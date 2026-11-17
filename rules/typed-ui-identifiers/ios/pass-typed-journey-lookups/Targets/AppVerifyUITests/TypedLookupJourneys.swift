import Foundation
import SettingsInterface
import XCTest

final class TypedLookupJourneys: XCTestCase {
    private let env: [String: String] = ["CI": "1"]

    func testTogglesNotifications() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: NotificationSettingsUIID.toggle)
        // Never app.switches["notificationSettings.toggle"]: find it by the constant.
        tapWhenHittable(screen.toggle(NotificationSettingsUIID.toggle))
        XCTAssertTrue(screen.find(NotificationSettingsUIID.toggle).exists)

        var built = [String: String]()
        built["a"] = "1"
        let notes: [String: String] = ["result": "toggled"]
        let lookup = { (values: [String: String]) in values["CI"] }
        XCTAssertEqual(notes["result"], "toggled")
        XCTAssertEqual(self.env["CI"], lookup(env))
        XCTAssertEqual(built["a"], "1")
        _ = ProcessInfo.processInfo.environment["CI"]
        _ = Locale(identifier: "en_US_POSIX")
        _ = TimeZone(identifier: "UTC")
        let site = "https://example.com"
        XCTAssertFalse(site.isEmpty)

        if screen.systemAlertButton("Allow").exists {
            screen.systemAlertButton("Allow").tap()
        }
        if screen.keyboardKey("Return").exists {
            screen.keyboardKey("Return").tap()
        }
    }
}
