import Core
import MeterInterface
import JourneyKit

extension UIID {
    static func invented(_ raw: String) -> UIID {
        self.init(raw)
    }
}

final class FactoryIDJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        tapWhenHittable(screen.find(UIID.invented("meter.increment")))
    }
}
