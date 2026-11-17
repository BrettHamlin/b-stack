import XCTest

final class LiteralLookupJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches["notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
