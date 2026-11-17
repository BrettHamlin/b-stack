import JourneyKit

final class HelperQueryJourneys: Journey {
    private func toggles(_ app: XCUIApplication) -> XCUIElementQuery {
        app.switches
    }

    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        toggles(app)["notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
