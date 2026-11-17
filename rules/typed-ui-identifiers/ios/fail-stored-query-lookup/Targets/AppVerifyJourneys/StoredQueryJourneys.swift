import JourneyKit

final class StoredQueryJourneys: Journey {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let controls = app.descendants(matching: .switch)
        controls["notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
