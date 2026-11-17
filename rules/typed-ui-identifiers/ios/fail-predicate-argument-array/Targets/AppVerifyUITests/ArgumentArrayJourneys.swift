import XCTest

final class ArgumentArrayJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let match = NSPredicate(format: "identifier == %@", argumentArray: ["notificationSettings.toggle"])
        app.switches.element(matching: match).tap()
    }
}
