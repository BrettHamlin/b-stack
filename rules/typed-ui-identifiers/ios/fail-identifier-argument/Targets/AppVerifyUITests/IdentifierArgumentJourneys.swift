import XCTest

final class IdentifierArgumentJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let switches = app.switches
        switches.matching(identifier: "notificationSettings.toggle").firstMatch.tap()
    }
}
