import MeterInterface
import JourneyKit

final class InferredIDJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        tapWhenHittable(screen.find(.init("meter.increment")))
    }
}
