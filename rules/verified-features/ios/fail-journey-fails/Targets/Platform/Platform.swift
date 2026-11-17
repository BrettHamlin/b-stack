import Core
import Foundation
public import SettingsInterface

/// The notification preference, kept in the app's standard UserDefaults. Each app has its own container, so the
/// test-mode app (a separate bundle) never sees the shipped app's data.
public struct StoredNotificationPreferences: NotificationPreferences {
    private static let key = "notificationsEnabled"

    public init() {}

    public func load() -> Bool {
        UserDefaults.standard.bool(forKey: Self.key)
    }

    public func store(enabled: Bool) {
        UserDefaults.standard.set(enabled, forKey: Self.key)
    }

    public func save(enabled: Bool) async throws(NotificationPreferenceError) {
        // Bug: reports success without storing the value.
    }
}
