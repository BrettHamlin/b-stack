import XCTest

final class SecondArgumentJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let match = NSPredicate(format: "label == %@ AND identifier == %@", "Notifications", "notificationSettings.toggle")
        app.switches.element(matching: match).tap()
    }
}
