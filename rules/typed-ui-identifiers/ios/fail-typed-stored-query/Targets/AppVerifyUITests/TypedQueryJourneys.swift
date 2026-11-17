import XCTest

final class TypedQueryJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let controls: XCUIElementQuery = app.switches
        controls["notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
