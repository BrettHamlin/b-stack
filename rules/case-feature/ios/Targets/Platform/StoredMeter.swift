import Foundation
public import MeterInterface

/// The meter's saved count, in the app's standard UserDefaults.
public struct StoredMeter: MeterStore {
    public init() {}

    public func load() -> Int {
        UserDefaults.standard.integer(forKey: "meterCount")
    }
}
