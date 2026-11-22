import Core
import MeterInterface
import JourneyKit

final class UnsafeIDJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        tapWhenHittable(screen.find(unsafeBitCast("meter.increment", to: UIID.self)))
    }
}
