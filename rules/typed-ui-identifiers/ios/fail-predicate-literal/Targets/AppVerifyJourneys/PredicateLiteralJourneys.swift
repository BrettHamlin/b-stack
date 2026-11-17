import JourneyKit

final class PredicateLiteralJourneys: Journey {
    func testTogglesNotifications() {
        let app = XCUIApplication()
        app.launch()
        app.switches.element(matching: NSPredicate(format: "identifier == 'notificationSettings.toggle'")).tap()
    }
}
