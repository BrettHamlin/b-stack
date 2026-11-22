import MeterInterface
import JourneyKit

final class KeyPathJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        let path = \XCUIElement.switches
        screen.find(MeterUIID.increment)[keyPath: path].firstMatch.tap()
    }
}
