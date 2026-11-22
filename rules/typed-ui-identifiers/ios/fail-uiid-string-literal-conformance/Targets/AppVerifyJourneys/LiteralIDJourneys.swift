public import Core
import MeterInterface
import JourneyKit

extension UIID: @retroactive ExpressibleByStringLiteral {
    public init(stringLiteral value: String) {
        self.init(value)
    }
}

final class LiteralIDJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        tapWhenHittable(screen.find("meter.increment"))
    }
}
