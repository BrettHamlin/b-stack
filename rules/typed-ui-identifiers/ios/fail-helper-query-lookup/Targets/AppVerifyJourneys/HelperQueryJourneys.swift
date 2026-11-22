import JourneyKit

final class HelperQueryJourneys: Journey {
    private func toggles(_ app: XCUIApplication) -> XCUIElementQuery {
        app.switches
    }

    func testAddsOne() {
        let app = XCUIApplication()
        app.launch()
        toggles(app)["meter.increment"].switches.firstMatch.tap()
    }
}
