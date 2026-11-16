import Core
import Foundation
public import SettingsInterface

/// The notification preference, kept in UserDefaults on the device.
public struct StoredNotificationPreferences: NotificationPreferenceSaving {
    private static let key = "notificationsEnabled"
    private let suiteName: String?

    public init(suiteName: String? = nil) {
        self.suiteName = suiteName
    }

    private var defaults: UserDefaults {
        suiteName.flatMap(UserDefaults.init(suiteName:)) ?? .standard
    }

    public func load() -> Bool {
        defaults.bool(forKey: Self.key)
    }

    public func store(enabled: Bool) {
        defaults.set(enabled, forKey: Self.key)
    }

    public func save(enabled: Bool) async throws(NotificationPreferenceError) {
        // Bug: reports success without storing the value.
    }
}
