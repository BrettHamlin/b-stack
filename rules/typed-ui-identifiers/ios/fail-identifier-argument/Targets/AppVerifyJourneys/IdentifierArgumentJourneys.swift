import JourneyKit

final class IdentifierArgumentJourneys: Journey {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        let switches = app.switches
        switches.matching(identifier: "notificationSettings.toggle").firstMatch.tap()
    }
}
