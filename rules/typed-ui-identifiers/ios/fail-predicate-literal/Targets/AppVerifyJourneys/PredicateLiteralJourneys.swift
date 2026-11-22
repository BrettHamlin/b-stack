import JourneyKit

final class PredicateLiteralJourneys: Journey {
    func testAddsOne() {
        let app = XCUIApplication()
        app.launch()
        app.switches.element(matching: NSPredicate(format: "identifier == 'meter.increment'")).tap()
    }
}
