public import Core

/// The largest count the meter shows.
public enum MeterLimit {
    public static let maximum = 99
}

/// Where a saved count lives. Platform implements it.
public protocol MeterStore: Sendable {
    func load() -> Int
}

/// Accessibility identifiers for the meter screen.
public enum MeterUIID {
    public static let increment = UIID("meter.increment")
    public static let count = UIID("meter.count")
    public static let reset = UIID("meter.reset")
}
