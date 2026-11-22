import JourneyKit

final class IdentifierArgumentJourneys: Journey {
    func testAddsOne() {
        let app = XCUIApplication()
        app.launch()
        let switches = app.switches
        switches.matching(identifier: "meter.increment").firstMatch.tap()
    }
}
