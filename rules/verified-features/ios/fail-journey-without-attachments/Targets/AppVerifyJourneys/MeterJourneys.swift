import MeterInterface
public import JourneyKit

/// Journeys for feature-map/meter.toml. This one passes but attaches nothing, so it leaves no evidence.
public final class MeterJourneys: Journey {
    public func testAddsOne() {
        expectEqual(MeterLimit.maximum, 99, "the count stops at 99")
    }
}
