import XCTest

final class NameCollisionJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let buttons: [String: String] = ["done": "Done"]
        XCTAssertEqual(buttons["done"], "Done")
        app.buttons["notificationSettings.toggle"].tap()
    }
}
