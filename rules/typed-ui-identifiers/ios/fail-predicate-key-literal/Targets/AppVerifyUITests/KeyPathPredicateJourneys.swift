import XCTest

final class KeyPathPredicateJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let match = NSPredicate(format: "%K == %@", "identifier", "notificationSettings.toggle")
        app.switches.element(matching: match).tap()
    }
}
