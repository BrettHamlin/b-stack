import XCTest

final class WrappedLiteralJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches[("notificationSettings.toggle")].tap()
        app.switches[String("notificationSettings.toggle")].tap()
    }
}
