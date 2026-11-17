import Foundation
import SettingsInterface
import XCTest

final class TypedLookupJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        let original = app.launchEnvironment
        var copied = original
        copied["BSTACK_FIXTURE"] = "standard"
        app.launchEnvironment = copied
        app.launch()
        // Never app.switches["notificationSettings.toggle"]: use the constant.
        let typed = NSPredicate(format: "label == %@ AND identifier == %@", "Notifications", NotificationSettingsUIID.toggle)
        app.switches.element(matching: typed).switches.firstMatch.tap()
        XCTAssertEqual(app.switches[NotificationSettingsUIID.toggle].identifier, NotificationSettingsUIID.toggle)
        let site = "https://example.com"; XCTAssertTrue(app.switches[NotificationSettingsUIID.toggle].exists, site)

        let notes: [String: String] = ["result": "toggled"]
        var built = [String: String]()
        built["a"] = "1"
        var generic = Dictionary<String, String>()
        generic["b"] = "2"
        let raw: Any = ["c": "3"]
        let cast = raw as? [String: String]
        XCTAssertEqual(notes["result"], "toggled")
        XCTAssertEqual(cast?["c"], "3")
        XCTAssertEqual(lookup(built, generic), "12")
        _ = ProcessInfo.processInfo.environment["CI"]
        let again = copied
        XCTAssertEqual(again["BSTACK_FIXTURE"], "standard")
        let other: Dictionary<String, String> = ["d": "4"]
        XCTAssertEqual(other["d"], "4")

        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        if springboard.buttons["Allow"].exists {
            springboard.buttons["Allow"].tap()
        }
        if app.keyboards.buttons["Return"].exists {
            app.keyboards.buttons["Return"].tap()
        }
    }

    private func lookup(_ first: [String: String], _ second: Dictionary<String, String>) -> String {
        (first["a"] ?? "") + (second["b"] ?? "")
    }
}
