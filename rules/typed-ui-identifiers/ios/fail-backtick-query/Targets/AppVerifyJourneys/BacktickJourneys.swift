import MeterInterface
import JourneyKit

final class BacktickJourneys: Journey {
    func testAddsOne() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        screen.find(MeterUIID.increment).`switches`["meter.increment"].tap()
    }
}
