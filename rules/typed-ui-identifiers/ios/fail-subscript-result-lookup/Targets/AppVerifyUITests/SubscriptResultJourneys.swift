import XCTest

final class SubscriptResultJourneys: XCTestCase {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let all = [app.switches]
        all[0]["notificationSettings.toggle"].tap()
        let toggles = ["all": app.switches]["all"]!
        toggles["notificationSettings.toggle"].tap()
    }
}
