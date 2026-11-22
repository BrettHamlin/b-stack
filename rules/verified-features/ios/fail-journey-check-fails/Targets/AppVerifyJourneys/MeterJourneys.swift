import MeterInterface
public import JourneyKit

/// Journeys for feature-map/meter.toml. This one's check doesn't hold: the count stops at 99, not 100.
public final class MeterJourneys: Journey {
    public func testAddsOne() {
        expectEqual(MeterLimit.maximum, 100, "the count stops at 100")
    }
}
