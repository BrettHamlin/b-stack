import XCTest

final class RawStringJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches[#"notificationSettings.toggle"#].switches.firstMatch.tap()
    }
}
