import XCTest

final class PredicateLiteralJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches.element(matching: NSPredicate(format: "identifier == 'notificationSettings.toggle'")).tap()
    }
}
