import XCTest

final class MarkerInStringJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        let open = "/*"
        app.launch()
        app.switches["notificationSettings.toggle"].switches.firstMatch.tap()
        let close = "*/"
        XCTAssertNotEqual(open, close)
    }
}
