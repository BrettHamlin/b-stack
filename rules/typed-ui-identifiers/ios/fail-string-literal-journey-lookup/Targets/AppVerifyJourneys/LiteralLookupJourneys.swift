import JourneyKit

final class LiteralLookupJourneys: Journey {
    func testAddsOne() {
        let app = XCUIApplication()
        app.launch()
        app.switches["meter.increment"].switches.firstMatch.tap()
    }
}
