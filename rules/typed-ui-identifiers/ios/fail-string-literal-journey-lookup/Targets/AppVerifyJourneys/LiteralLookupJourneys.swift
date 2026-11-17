import JourneyKit

final class LiteralLookupJourneys: Journey {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches["notificationSettings.toggle"].switches.firstMatch.tap()
    }
}
