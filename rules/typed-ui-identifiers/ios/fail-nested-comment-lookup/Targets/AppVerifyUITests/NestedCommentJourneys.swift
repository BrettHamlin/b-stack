import XCTest

final class NestedCommentJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches[/* outer /* inner */ outer */ "notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
