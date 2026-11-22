import MeterInterface
public import JourneyKit

public final class IndexedJourneys: Journey {
    public func testFindsAnIndexedCell() {
        let screen = launchApp(fixture: "standard", reset: true, readyWhen: MeterUIID.increment)
        expectFalse(screen.find(MeterUIID.increment, at: 3, 5).exists)
    }
}
