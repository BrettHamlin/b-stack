@testable import Core
import MeterInterface
import JourneyKit

final class TestableIDJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        tapWhenHittable(screen.find(UIID("meter.increment")))
    }
}
