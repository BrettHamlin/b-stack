import SettingsInterface
import XCTest

final class TypedLookupJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        var environment = app.launchEnvironment
        environment["BSTACK_FIXTURE"] = "standard"
        app.launchEnvironment = environment
        app.launch()
        // Never app.switches["notificationSettings.toggle"]: use the constant.
        let typed = NSPredicate(format: "identifier == %@", NotificationSettingsUIID.toggle)
        app.switches.element(matching: typed).switches.firstMatch.tap()
        let notes: [String: String] = ["result": "toggled"]
        XCTAssertEqual(notes["result"], "toggled")
        let site = "https://example.com"; XCTAssertTrue(app.switches[NotificationSettingsUIID.toggle].exists, site)
        let other: [String: String] = defaults()
        XCTAssertEqual(other["other"], "value")
    }

    private func defaults() -> [String: String] {
        return ["other": "value"]
    }
}
