import SettingsInterface
import XCTest

final class TypedLookupJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launchEnvironment["BSTACK_FIXTURE"] = "standard"
        app.launch()
        // Never app.switches["notificationSettings.toggle"]: use the constant.
        let typed = NSPredicate(format: "identifier == %@", NotificationSettingsUIID.toggle)
        app.switches.element(matching: typed).switches.firstMatch.tap()
        let notes: [String: String] = ["result": "toggled"]
        XCTAssertEqual(notes["result"], "toggled")
        XCTAssertEqual(app.switches[NotificationSettingsUIID.toggle].identifier, NotificationSettingsUIID.toggle)
    }
}
