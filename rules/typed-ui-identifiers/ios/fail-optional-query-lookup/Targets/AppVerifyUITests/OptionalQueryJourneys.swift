import XCTest

final class OptionalQueryJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let query: XCUIElementQuery? = app.switches
        query?["notificationSettings.toggle"].tap()
    }
}
