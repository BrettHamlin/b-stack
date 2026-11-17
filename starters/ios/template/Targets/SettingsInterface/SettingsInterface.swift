public import Core

public struct NotificationPreferenceError: Error, Equatable, Sendable {
    public let message: String
    public init(message: String) { self.message = message }
}

public protocol NotificationPreferenceSaving: Sendable {
    func save(enabled: Bool) async throws(NotificationPreferenceError)
}

/// Where the notification preference lives: its saved value, and how to save a new one. The shipped app and the
/// test-mode app both hand one of these to the settings screen, which loads from it, so neither can skip the load.
public protocol NotificationPreferences: NotificationPreferenceSaving {
    func load() -> Bool
}

/// Accessibility identifiers for the notification settings screen. The view sets them and the UI journeys find
/// elements by them, so a renamed or mistyped identifier is a compile error rather than a journey that can't find
/// its element.
public enum NotificationSettingsUIID {
    public static let toggle = UIID("notificationSettings.toggle")
    public static let saving = UIID("notificationSettings.saving")
    public static let error = UIID("notificationSettings.error")
}
