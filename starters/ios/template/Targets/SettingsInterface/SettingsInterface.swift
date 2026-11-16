import Core

public struct NotificationPreferenceError: Error, Equatable, Sendable {
    public let message: String
    public init(message: String) { self.message = message }
}

public protocol NotificationPreferenceSaving: Sendable {
    func save(enabled: Bool) async throws(NotificationPreferenceError)
}

/// Accessibility identifiers for the notification settings screen. The view sets them and the UI journeys find
/// elements by them, so a renamed or mistyped identifier is a compile error rather than a journey that can't find
/// its element.
public enum NotificationSettingsUIID {
    public static let toggle = "notificationSettings.toggle"
    public static let saving = "notificationSettings.saving"
    public static let error = "notificationSettings.error"
}
