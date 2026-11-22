import MeterInterface
import JourneyKit

final class RawConstantJourneys: Journey {
    func testAddsOne() {
        let app = XCUIApplication()
        app.launch()
        app.switches[MeterUIID.increment.rawValue].tap()
    }
}
