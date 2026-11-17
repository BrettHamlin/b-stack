import XCTest

final class PredicateArgumentJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let toggle = NSPredicate(format: "identifier == %@", "notificationSettings.toggle")
        app.switches.element(matching: toggle).switches.firstMatch.tap()
    }
}
