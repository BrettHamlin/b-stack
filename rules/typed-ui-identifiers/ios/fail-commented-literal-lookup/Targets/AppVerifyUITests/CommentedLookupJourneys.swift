import XCTest

final class CommentedLookupJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches[/* toggle */ "notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
