import JourneyKit

final class StoredQueryJourneys: Journey {
    func testAddsOne() {
        let app = XCUIApplication()
        app.launch()
        let controls = app.descendants(matching: .switch)
        controls["meter.increment"].switches.firstMatch.tap()
    }
}
