import MeterInterface
import JourneyKit

final class StringIDJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        tapWhenHittable(screen.find("meter.increment"))
    }
}
