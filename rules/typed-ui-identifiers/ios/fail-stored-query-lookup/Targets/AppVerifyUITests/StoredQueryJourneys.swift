import XCTest

final class StoredQueryJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let controls = app.descendants(matching: .switch)
        controls["notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
